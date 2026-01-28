import React, { useEffect, useState } from 'react';
import * as d3 from 'd3';
import './d3-dashboard.css';

function D3Dashboard({ setCurrentPage }) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const userId = localStorage.getItem('user_id');

  useEffect(() => {
    fetchTransactions();
  }, []);

  useEffect(() => {
    if (data.length > 0) {
      initializeDashboard(data);
    }
  }, [data]);

  const fetchTransactions = async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/transactions?user_id=${userId}&page_size=1000`);
      const result = await response.json();
      
      if (response.ok && result.transactions.length > 0) {
        const transformedData = result.transactions.map(txn => ({
          transaction_id: txn.transaction_id,
          timestamp: formatTimestamp(txn.transaction_date),
          amount: txn.amount,
          category: txn.category || 'Other',
          merchant: txn.merchant || '',
        }));

        setData(transformedData);
        setLoading(false);
      } else {
        setLoading(false);
      }
    } catch (error) {
      console.error('Error fetching transactions:', error);
      setLoading(false);
    }
  };

  const formatTimestamp = (dateStr) => {
    const date = new Date(dateStr);
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${day}-${month}-${year} ${hours}:${minutes}`;
  };

  const handleLogout = () => {
    localStorage.removeItem('user_id');
    localStorage.removeItem('email');
    setCurrentPage('login');
  };

  const handleBack = () => {
    setCurrentPage('dashboard');
  };

  const initializeDashboard = (rawData) => {
    rawData.forEach(d => {
      d.parsedTime = parseTimestamp(d.timestamp);
      d.dateOnly = d.parsedTime ? d.parsedTime.date : null;
      d.timeOnly = d.parsedTime ? d.parsedTime.time : null;
      d.amountNum = +d.amount;
      d.category = d.category || "Other";
      d.merchant = d.merchant || "";
      d.timeBucket = timeBucket(d.timeOnly);
    });

    const cleanData = rawData.filter(d => !isNaN(d.amountNum) && d.parsedTime);

    buildPie(cleanData);
    buildLine(cleanData);
    buildTimeBuckets(cleanData);
    buildScatter(cleanData);
    buildTopAndLowTables(cleanData);
    buildAnomalies(cleanData);
  };

  function parseTimestamp(ts) {
    if (!ts) return null;
    const parts = ts.split(" ");
    if (parts.length < 2) return null;
    const [dateStr, timeStr] = parts;
    const [d, m, y] = dateStr.split("-").map(Number);
    const [H, M] = timeStr.split(":").map(Number);
    const dateObj = new Date(y, m - 1, d, H, M);
    return {
      full: dateObj,
      date: new Date(y, m - 1, d),
      time: { hour: H, minute: M }
    };
  }

  function timeBucket(timeObj) {
    if (!timeObj) return "Unknown";
    const h = timeObj.hour;
    if (h < 6) return "Night (00–06)";
    if (h < 12) return "Morning (06–12)";
    if (h < 18) return "Afternoon (12–18)";
    return "Evening (18–24)";
  }

  function buildPie(data) {
    const byCat = d3.rollups(
      data,
      v => d3.sum(v, d => d.amountNum),
      d => d.category
    ).map(([category, total]) => ({ category, total }));

    const totalAll = d3.sum(byCat, d => d.total);
    d3.select("#pieMeta").text("Total spent: €" + totalAll.toFixed(2));

    const container = d3.select("#pieChart");
    container.selectAll("*").remove();

    const width = container.node()?.clientWidth || 380;
    const height = container.node()?.clientHeight || 380;
    const radius = Math.min(width, height) / 2 - 18;

    const svg = container.append("svg")
      .attr("viewBox", `0 0 ${width} ${height}`);

    const g = svg.append("g")
      .attr("transform", `translate(${width / 2}, ${height / 2})`);

    const palette = [
      "#3b82f6", "#10b981", "#f97316", "#ec4899", "#eab308", "#6366f1"
    ];

    const color = d3.scaleOrdinal()
      .domain(byCat.map(d => d.category))
      .range(byCat.map((_, i) => palette[i % palette.length]));

    const pie = d3.pie().sort(null).value(d => d.total);
    const arc = d3.arc().innerRadius(radius * 0.45).outerRadius(radius);
    const arcHover = d3.arc().innerRadius(radius * 0.43).outerRadius(radius + 8);

    const tooltip = makeTooltip(container);

    g.selectAll("path.segment")
      .data(pie(byCat))
      .join("path")
      .attr("class", "segment")
      .attr("fill", d => color(d.data.category))
      .attr("stroke", "#020617")
      .attr("stroke-width", 1.5)
      .attr("d", arc)
      .on("mouseover", function (event, d) {
        d3.select(this).transition().duration(120).attr("d", arcHover);
        const pct = (d.data.total / totalAll) * 100;
        tooltip.style("display", "block").html(
          `<strong>${d.data.category}</strong><br>€${d.data.total.toFixed(2)} · ${pct.toFixed(1)}%`
        );
      })
      .on("mousemove", function (event) {
        tooltip.style("left", event.offsetX + 12 + "px").style("top", event.offsetY + 12 + "px");
      })
      .on("mouseout", function () {
        d3.select(this).transition().duration(120).attr("d", arc);
        tooltip.style("display", "none");
      });

    const legend = d3.select("#pieLegend");
    legend.selectAll("*").remove();
    const legendItems = legend.selectAll(".legend-item")
      .data(byCat.sort((a, b) => d3.descending(a.total, b.total)))
      .join("div").attr("class", "legend-item");

    legendItems.append("span").attr("class", "legend-swatch").style("background", d => color(d.category));
    legendItems.append("span").text(d => {
      const pct = (d.total / totalAll) * 100;
      return `${d.category} (${pct.toFixed(1)}%)`;
    });
  }

  function buildLine(data) {
    const byDate = d3.rollups(data, v => d3.sum(v, d => d.amountNum), d => +d.dateOnly)
      .map(([ts, total]) => ({ date: new Date(ts), total }))
      .sort((a, b) => d3.ascending(a.date, b.date));

    const totalAll = d3.sum(byDate, d => d.total);
    d3.select("#lineMeta").text("Days: " + byDate.length + " · Total €" + totalAll.toFixed(2));

    const container = d3.select("#lineChart");
    container.selectAll("*").remove();

    const width = container.node()?.clientWidth || 260;
    const height = container.node()?.clientHeight || 220;
    const margin = { top: 10, right: 20, bottom: 24, left: 40 };

    const svg = container.append("svg").attr("viewBox", `0 0 ${width} ${height}`);

    const x = d3.scaleTime().domain(d3.extent(byDate, d => d.date)).range([margin.left, width - margin.right]);
    const y = d3.scaleLinear().domain([0, d3.max(byDate, d => d.total) * 1.1]).nice().range([height - margin.bottom, margin.top]);

    const line = d3.line().x(d => x(d.date)).y(d => y(d.total)).curve(d3.curveMonotoneX);
    const area = d3.area().x(d => x(d.date)).y0(height - margin.bottom).y1(d => y(d.total)).curve(d3.curveMonotoneX);

    svg.append("path").datum(byDate).attr("fill", "rgba(59, 130, 246, 0.15)").attr("d", area);
    svg.append("path").datum(byDate).attr("fill", "none").attr("stroke", "#3b82f6").attr("stroke-width", 2).attr("d", line);

    svg.append("g").attr("transform", `translate(0,${height - margin.bottom})`).call(d3.axisBottom(x).ticks(5).tickFormat(d3.timeFormat("%d-%m")));
    svg.append("g").attr("transform", `translate(${margin.left},0)`).call(d3.axisLeft(y).ticks(4));
  }

  function buildTimeBuckets(data) {
    const grouped = d3.rollups(data, v => d3.sum(v, d => d.amountNum), d => d.timeBucket)
      .map(([label, total]) => ({ label, total }))
      .sort((a, b) => {
        const order = ["Night (00–06)", "Morning (06–12)", "Afternoon (12–18)", "Evening (18–24)"];
        return order.indexOf(a.label) - order.indexOf(b.label);
      });

    const container = d3.select("#barChart");
    container.selectAll("*").remove();

    const width = container.node()?.clientWidth || 260;
    const height = container.node()?.clientHeight || 220;
    const margin = { top: 10, right: 10, bottom: 40, left: 50 };

    const svg = container.append("svg").attr("viewBox", `0 0 ${width} ${height}`);
    const x = d3.scaleBand().domain(grouped.map(d => d.label)).range([margin.left, width - margin.right]).padding(0.35);
    const y = d3.scaleLinear().domain([0, d3.max(grouped, d => d.total) * 1.1]).nice().range([height - margin.bottom, margin.top]);

    const colors = ["#6366f1", "#10b981", "#eab308", "#f97316"];

    svg.selectAll(".bar").data(grouped).join("rect")
      .attr("class", "bar")
      .attr("x", d => x(d.label))
      .attr("y", d => y(d.total))
      .attr("width", x.bandwidth())
      .attr("height", d => y(0) - y(d.total))
      .attr("fill", (d, i) => colors[i % colors.length]);

    svg.append("g").attr("transform", `translate(0,${height - margin.bottom})`).call(d3.axisBottom(x));
    svg.append("g").attr("transform", `translate(${margin.left},0)`).call(d3.axisLeft(y).ticks(4));
  }

  function buildScatter(data) {
    const categories = Array.from(new Set(data.map(d => d.category))).sort();
    const select = d3.select("#scatterCategorySelect");

    select.selectAll("option.category-option").data(categories).join("option")
      .attr("class", "category-option").attr("value", d => d).text(d => d);

    const container = d3.select("#scatterChart");
    container.selectAll("*").remove();

    const width = container.node()?.clientWidth || 260;
    const height = container.node()?.clientHeight || 220;
    const margin = { top: 10, right: 14, bottom: 24, left: 40 };

    const svg = container.append("svg").attr("viewBox", `0 0 ${width} ${height}`);
    const x = d3.scaleTime().domain(d3.extent(data, d => d.parsedTime.full)).range([margin.left, width - margin.right]);
    const y = d3.scaleLinear().domain([0, d3.max(data, d => d.amountNum) * 1.1]).nice().range([height - margin.bottom, margin.top]);

    svg.append("g").attr("transform", `translate(0,${height - margin.bottom})`).call(d3.axisBottom(x).ticks(4).tickFormat(d3.timeFormat("%d-%m")));
    svg.append("g").attr("transform", `translate(${margin.left},0)`).call(d3.axisLeft(y).ticks(4));

    function renderScatter(filterCat) {
      const filtered = filterCat && filterCat !== "All" ? data.filter(d => d.category === filterCat) : data;
      svg.selectAll("circle.point").data(filtered, d => d.transaction_id)
        .join("circle")
        .attr("class", "point")
        .attr("cx", d => x(d.parsedTime.full))
        .attr("cy", d => y(d.amountNum))
        .attr("r", 2.8)
        .attr("fill", "rgba(234, 179, 8, 0.6)")
        .attr("stroke", "#0f172a")
        .attr("stroke-width", 0.6);
    }

    renderScatter("All");
    select.on("change", event => renderScatter(event.target.value));
  }

  function buildTopAndLowTables(data) {
    const sortedAsc = [...data].sort((a, b) => d3.ascending(a.amountNum, b.amountNum));
    const sortedDesc = [...data].sort((a, b) => d3.descending(a.amountNum, b.amountNum));

    fillTable("#topTable tbody", sortedDesc.slice(0, 10));
    fillTable("#lowTable tbody", sortedAsc.slice(0, 10));
  }

  function fillTable(selector, rowsData) {
    const tbody = d3.select(selector);
    tbody.selectAll("tr").remove();

    const rows = tbody.selectAll("tr").data(rowsData).join("tr");
    rows.append("td").text(d => d3.timeFormat("%d-%m-%Y")(d.dateOnly));
    rows.append("td").text(d => d.merchant);
    rows.append("td").text(d => d.category);
    rows.append("td").text(d => "€" + d.amountNum.toFixed(2));
    rows.append("td").text(d => d3.timeFormat("%H:%M")(d.parsedTime.full));
  }

  function buildAnomalies(data) {
    const mean = d3.mean(data, d => d.amountNum);
    const sd = d3.deviation(data, d => d.amountNum) || 0;
    const threshold = mean + 2 * sd;
    const anomalies = data.filter(d => d.amountNum > threshold);

    d3.select("#anomalyMeta").text(
      anomalies.length ? `Threshold: €${threshold.toFixed(2)} · Found ${anomalies.length}` : "No strong outliers found"
    );

    const list = d3.select("#anomalyList");
    list.selectAll("*").remove();

    if (!anomalies.length) {
      list.append("div").attr("class", "anomaly-item").text("No amounts above mean + 2σ for this month.");
      return;
    }

    list.selectAll(".anomaly-item").data(anomalies.sort((a, b) => d3.descending(a.amountNum, b.amountNum)))
      .join("div").attr("class", "anomaly-item")
      .html(d => `
        <div><span class="anomaly-tag">High spend</span> · €${d.amountNum.toFixed(2)}</div>
        <div>${d3.timeFormat("%d-%m-%Y %H:%M")(d.parsedTime.full)} · ${d.merchant} · ${d.category}</div>
      `);
  }

  function makeTooltip(container) {
    let div = container.select(".tooltip");
    if (!div.size()) {
      div = container.append("div").attr("class", "tooltip").style("display", "none");
    }
    return div;
  }

  if (loading) {
    return (
      <div className="d3-loading">
        <div className="spinner"></div>
        <p>Loading your dashboard...</p>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="d3-loading">
        <h2>No Data Available</h2>
        <p>Upload a CSV to see your dashboard</p>
        <button onClick={handleBack}>Go Back</button>
      </div>
    );
  }

  return (
    <div className="d3-wrapper">
      <div className="header">
        <div>
          <h1>Spending Dashboard</h1>
          <div className="subtitle">Your Financial Data</div>
        </div>
        <div className="header-actions">
          <button onClick={handleBack} className="back-btn">← Back</button>
          <button onClick={handleLogout} className="logout-btn">Logout</button>
        </div>
      </div>

      <div className="dashboard">
        <div className="card card-line">
          <div className="card-header">
            <div className="card-title">Daily spend</div>
            <div className="card-meta" id="lineMeta"></div>
          </div>
          <div className="chart" id="lineChart"></div>
        </div>

        <div className="card card-pie">
          <div className="card-header">
            <div className="card-title">Category share</div>
            <div className="card-meta" id="pieMeta"></div>
          </div>
          <div className="chart" id="pieChart"></div>
          <div className="legend" id="pieLegend"></div>
        </div>

        <div className="card card-morning-night">
          <div className="card-header">
            <div className="card-title">Time of day</div>
            <div className="card-meta">Amounts summed by time window</div>
          </div>
          <div className="chart" id="barChart"></div>
        </div>

        <div className="card card-scatter">
          <div className="card-header">
            <div className="card-title">Transactions scatter</div>
            <div className="card-meta">Filter by category and hover for details</div>
          </div>
          <div className="controls">
            <label>
              <span style={{marginRight: '4px'}}>Category:</span>
              <select id="scatterCategorySelect">
                <option value="All">All</option>
              </select>
            </label>
          </div>
          <div className="chart" id="scatterChart"></div>
        </div>

        <div className="card card-top">
          <div className="card-header">
            <div className="card-title">Top & lowest transactions</div>
            <div className="card-meta">Top 10 highest · 10 lowest</div>
          </div>
          <div className="tables-wrapper">
            <div className="table-block">
              <div className="table-title">Top 10 highest</div>
              <table className="table" id="topTable">
                <thead><tr><th>Date</th><th>Merchant</th><th>Category</th><th>Amount</th><th>Time</th></tr></thead>
                <tbody></tbody>
              </table>
            </div>
            <div className="table-block">
              <div className="table-title">Top 10 lowest</div>
              <table className="table" id="lowTable">
                <thead><tr><th>Date</th><th>Merchant</th><th>Category</th><th>Amount</th><th>Time</th></tr></thead>
                <tbody></tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="card card-anomalies">
          <div className="card-header">
            <div className="card-title">Anomalies</div>
            <div className="card-meta" id="anomalyMeta"></div>
          </div>
          <div className="anomaly-list" id="anomalyList"></div>
        </div>
      </div>
    </div>
  );
}

export default D3Dashboard;