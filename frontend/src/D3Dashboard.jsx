import React, { useEffect, useState } from 'react';
import * as d3 from 'd3';
import './d3-dashboard.css';

function D3Dashboard({ setCurrentPage }) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [tableFilter, setTableFilter] = useState('highest');
  const MAX_RETRIES = 5;
  const RETRY_DELAY = 3000;

  const userId = localStorage.getItem('user_id');

  useEffect(() => {
    fetchTransactions();
  }, [userId]);

  useEffect(() => {
    if (data.length > 0) {
      initializeDashboard(data);
    }
  }, [data, tableFilter]);

  useEffect(() => {
    let timer;
    if (processing && retryCount < MAX_RETRIES && data.length === 0) {
      timer = setTimeout(() => {
        fetchTransactions(true);
      }, RETRY_DELAY);
    } else if (retryCount >= MAX_RETRIES) {
      setProcessing(false);
      setLoading(false);
    }
    return () => clearTimeout(timer);
  }, [processing, retryCount, data.length]);

  const fetchTransactions = async (isRetry = false) => {
    if (!isRetry) {
      setLoading(true);
      setRetryCount(0);
      setProcessing(false);
    }

    try {
      const response = await fetch(`http://localhost:8000/api/transactions?user_id=${userId}&page_size=10000`);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();

      if (result.transactions && result.transactions.length > 0) {
        const transformedData = result.transactions.map(txn => {
          const parsed = parseTimestamp(txn.timestamp);
          const amt = +txn.amount;
          const tOnly = parsed ? parsed.time : null;

          return {
            transaction_id: txn.transaction_id,
            timestamp: txn.timestamp,
            amount: txn.amount,
            amountNum: amt,
            category: txn.category || 'Other',
            merchant: txn.merchant || '',
            parsedTime: parsed,
            dateOnly: parsed ? parsed.date : null,
            timeOnly: tOnly,
            timeBucket: timeBucket(tOnly)
          };
        }).filter(d => !isNaN(d.amountNum) && d.parsedTime);

        setData(transformedData);
        setLoading(false);
        setProcessing(false);
      } else {
        if (isRetry || retryCount < MAX_RETRIES) {
          setProcessing(true);
          setLoading(false);
          if (isRetry) setRetryCount(prev => prev + 1);
        } else {
          setLoading(false);
          setProcessing(false);
        }
      }
    } catch (error) {
      console.error('Error fetching transactions:', error);
      if (retryCount < MAX_RETRIES) {
        setProcessing(true);
        if (isRetry) setRetryCount(prev => prev + 1);
      } else {
        setLoading(false);
        setProcessing(false);
      }
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('user_id');
    localStorage.removeItem('email');
    setCurrentPage('login');
  };

  const handleBack = () => {
    setCurrentPage('dashboard');
  };

  const initializeDashboard = (cleanData) => {
    buildPie(cleanData);
    buildLine(cleanData);
    buildTimeBuckets(cleanData);
    buildScatter(cleanData);
    buildAnomalies(cleanData);
  };

  function parseTimestamp(ts) {
    if (!ts) return null;
    const dateObj = new Date(ts);
    if (isNaN(dateObj.getTime())) return null;

    return {
      full: dateObj,
      date: new Date(dateObj.getFullYear(), dateObj.getMonth(), dateObj.getDate()),
      time: { hour: dateObj.getHours(), minute: dateObj.getMinutes() }
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
    const margin = { top: 10, right: 14, bottom: 24, left: 55 }; // Increased left margin

    const svg = container.append("svg").attr("viewBox", `0 0 ${width} ${height}`);

    const maxAmount = d3.max(data, d => d.amountNum);
    const x = d3.scaleTime().domain(d3.extent(data, d => d.parsedTime.full)).range([margin.left, width - margin.right]);
    const y = d3.scaleLinear().domain([0, maxAmount * 1.25]).nice().range([height - margin.bottom, margin.top]); // Increased from 1.1 to 1.25

    svg.append("g")
      .attr("transform", `translate(0,${height - margin.bottom})`)
      .call(d3.axisBottom(x).ticks(4).tickFormat(d3.timeFormat("%d-%m")))
      .selectAll("text")
      .style("font-size", "9px");

    svg.append("g")
      .attr("transform", `translate(${margin.left},0)`)
      .call(d3.axisLeft(y).ticks(6)) // Increased ticks from 4 to 6
      .selectAll("text")
      .style("font-size", "9px");

    const tooltip = makeTooltip(container);

    function renderScatter(filterCat) {
      const filtered = filterCat && filterCat !== "All" ? data.filter(d => d.category === filterCat) : data;

      const jitterAmount = 4;

      svg.selectAll("circle.point").data(filtered, d => d.transaction_id)
        .join("circle")
        .attr("class", "point")
        .attr("cx", d => x(d.parsedTime.full) + (Math.random() - 0.5) * 2)
        .attr("cy", d => y(d.amountNum) + (Math.random() - 0.5) * jitterAmount)
        .attr("r", 3.2)
        .attr("fill", "rgba(59, 130, 246, 0.6)")
        .attr("stroke", "#0f172a")
        .attr("stroke-width", 0.8)
        .on("mouseover", function (event, d) {
          d3.select(this).attr("r", 5).attr("fill", "rgba(59, 130, 246, 1)");
          tooltip.style("display", "block").html(
            `<strong>${d.merchant}</strong><br>€${d.amountNum.toFixed(2)} · ${d.category}<br>${d3.timeFormat("%d-%m-%Y %H:%M")(d.parsedTime.full)}`
          );
        })
        .on("mousemove", function (event) {
          tooltip.style("left", event.offsetX + 12 + "px").style("top", event.offsetY + 12 + "px");
        })
        .on("mouseout", function () {
          d3.select(this).attr("r", 3.2).attr("fill", "rgba(59, 130, 246, 0.6)");
          tooltip.style("display", "none");
        });
    }

    renderScatter("All");
    select.on("change", event => renderScatter(event.target.value));
  }

  function getRankedData() {
    if (!data || data.length === 0) return [];
    const filtered = data.filter(d => d.parsedTime && d.parsedTime.date);
    const sorted = [...filtered].sort((a, b) =>
      tableFilter === 'highest' ? d3.descending(a.amountNum, b.amountNum) : d3.ascending(a.amountNum, b.amountNum)
    );
    return sorted.slice(0, 10);
  }

  function buildAnomalies(data) {
    const mean = d3.mean(data, d => d.amountNum);
    const sd = d3.deviation(data, d => d.amountNum) || 0;
    const threshold = mean + 3 * sd;
    const anomalies = data.filter(d => d.amountNum > threshold)
      .sort((a, b) => d3.descending(a.amountNum, b.amountNum));

    d3.select("#anomalyMeta").text(
      anomalies.length ? `Threshold: €${threshold.toFixed(2)} · Found ${anomalies.length}` : "No strong outliers found"
    );

    const list = d3.select("#anomalyList");
    list.selectAll("*").remove();

    if (!anomalies.length) {
      list.append("div").attr("class", "anomaly-item").text("No amounts above mean + 3σ for this month.");
      return;
    }

    list.selectAll(".anomaly-item").data(anomalies.slice(0, 3))
      .join("div").attr("class", "anomaly-item")
      .html(d => `
        <div><span class="anomaly-tag">Critical outlier</span> · €${d.amountNum.toFixed(2)}</div>
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

  if (loading || (processing && data.length === 0)) {
    return (
      <div className="d3-loading">
        <div className="spinner"></div>
        <p>{processing ? `Still processing your data... (Attempt ${retryCount}/${MAX_RETRIES})` : 'Loading your dashboard...'}</p>
        <button onClick={handleBack} style={{ marginTop: '10px', background: '#374151' }}>Cancel</button>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="d3-loading">
        <h2>No Data Available</h2>
        <p>We couldn't find any transaction data for your account.</p>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button onClick={handleBack}>Go Back</button>
          <button onClick={() => fetchTransactions()} style={{ background: '#3b82f6', color: 'white' }}>Refresh</button>
        </div>
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
              <span style={{ marginRight: '4px' }}>Category:</span>
              <select id="scatterCategorySelect">
                <option value="All">All</option>
              </select>
            </label>
          </div>
          <div className="chart" id="scatterChart"></div>
        </div>

        <div className="card card-top">
          <div className="card-header">
            <div className="card-title">Transaction Rankings</div>
            <div className="toggle-container">
              <button
                className={`toggle-btn ${tableFilter === 'highest' ? 'active' : ''}`}
                onClick={() => setTableFilter('highest')}
              >
                Highest
              </button>
              <button
                className={`toggle-btn ${tableFilter === 'lowest' ? 'active' : ''}`}
                onClick={() => setTableFilter('lowest')}
              >
                Lowest
              </button>
            </div>
          </div>
          <div className="tables-wrapper">
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Merchant</th>
                    <th>Category</th>
                    <th>Amount</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {getRankedData().map((d) => (
                    <tr key={d.transaction_id}>
                      <td>{d3.timeFormat("%d-%m-%Y")(d.parsedTime.date)}</td>
                      <td>{d.merchant}</td>
                      <td>{d.category}</td>
                      <td>€{d.amountNum.toFixed(2)}</td>
                      <td>{d3.timeFormat("%H:%M")(d.parsedTime.full)}</td>
                    </tr>
                  ))}
                </tbody>
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
