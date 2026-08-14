import { useState } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell, PieChart, Pie, Legend,
} from 'recharts';
import { useFetchAnalyticsSummaryQuery } from '../../api/complaintsApi';
import styles from './Dashboard.module.css';

/* ─── Color Tokens ─── */
const SEVERITY_COLORS = {
  critical:   '#ef4444',
  major:      '#f59e0b',
  minor:      '#22c55e',
  unassessed: '#8b5cf6',
};

const CATEGORY_COLORS = ['#3b82f6', '#ec4899', '#f97316', '#64748b'];

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className={styles.customTooltip}>
        <div className={styles.tooltipTitle}>{label}</div>
        {payload.map((entry, index) => (
          <div key={index} className={styles.tooltipItem} style={{ color: entry.color }}>
            <span>{entry.name}:</span>
            <strong>{entry.value}</strong>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

/**
 * Dashboard — Pharmaceutical Quality Analytics & Complaint Trend View.
 */
export default function Dashboard() {
  const [days, setDays] = useState(30);
  const { data: analytics, isLoading, isError } = useFetchAnalyticsSummaryQuery(days);

  if (isLoading) {
    return (
      <div className={styles.page}>
        <div className={styles.loadingWrapper}>
          <div className={styles.spinner} />
          Loading quality analytics summary…
        </div>
      </div>
    );
  }

  if (isError || !analytics) {
    return (
      <div className={styles.page}>
        <div className={styles.header}>
          <div>
            <h1 className={styles.title}>Quality Analytics &amp; Complaint Trends</h1>
            <p className={styles.subtitle}>Could not load analytics summary. Please check backend connection.</p>
          </div>
        </div>
      </div>
    );
  }

  const {
    total_complaints = 0,
    critical_count = 0,
    unassessed_count = 0,
    active_investigations = 0,
    severity_breakdown = [],
    category_breakdown = [],
    top_products = [],
    trends_over_time = [],
  } = analytics || {};

  return (
    <div className={styles.page}>

      {/* ── Header & Timeframe Selector ── */}
      <div className={styles.header}>
        <div>
          <h1 className={styles.title}>Quality Analytics &amp; Complaint Trends</h1>
          <p className={styles.subtitle}>
            Executive QMS Dashboard · Product quality defect metrics over the past {days} days
          </p>
        </div>

        <div className={styles.timeframeSelector}>
          {[30, 60, 90].map(d => (
            <button
              key={d}
              className={`${styles.timeframeBtn} ${days === d ? styles.timeframeBtnActive : ''}`}
              onClick={() => setDays(d)}
            >
              Last {d} Days
            </button>
          ))}
        </div>
      </div>

      {/* ── KPI Metric Cards ── */}
      <div className={styles.kpiGrid}>
        <div className={styles.kpiCard}>
          <div className={styles.kpiLabel}>Total Intake Complaints</div>
          <div className={styles.kpiValueRow}>
            <div className={styles.kpiValue}>{total_complaints}</div>
            <span className={`${styles.kpiTag} ${styles.kpiMinor}`}>All Time</span>
          </div>
        </div>

        <div className={styles.kpiCard}>
          <div className={styles.kpiLabel}>Critical Severity Defect</div>
          <div className={styles.kpiValueRow}>
            <div className={styles.kpiValue}>{critical_count}</div>
            <span className={`${styles.kpiTag} ${styles.kpiCritical}`}>High Risk</span>
          </div>
        </div>

        <div className={styles.kpiCard}>
          <div className={styles.kpiLabel}>Active Investigations</div>
          <div className={styles.kpiValueRow}>
            <div className={styles.kpiValue}>{active_investigations}</div>
            <span className={`${styles.kpiTag} ${styles.kpiMajor}`}>Open QA</span>
          </div>
        </div>

        <div className={styles.kpiCard}>
          <div className={styles.kpiLabel}>Pending AI Triage</div>
          <div className={styles.kpiValueRow}>
            <div className={styles.kpiValue}>{unassessed_count}</div>
            <span className={`${styles.kpiTag} ${styles.kpiPending}`}>Action Req</span>
          </div>
        </div>
      </div>

      {/* ── Charts Grid ── */}
      <div className={styles.chartsGrid}>

        {/* 1. Complaints Trend Over Time (Area Chart) */}
        <div className={`${styles.chartCard} ${styles.chartCardSpan8}`}>
          <div className={styles.header}>
            <div>
              <h3 className={styles.chartTitle}>Complaint Intake Volume Over Time</h3>
              <p className={styles.chartSubtitle}>Daily breakdown by severity tier (Last {days} Days)</p>
            </div>
          </div>
          <div className={styles.chartBody}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trends_over_time} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="gradCrit" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="gradMaj" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="gradMin" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(220, 15%, 92%)" />
                <XAxis dataKey="date" tickLine={false} tick={{ fontSize: 11, fill: 'hsl(220, 10%, 50%)' }} />
                <YAxis allowDecimals={false} tickLine={false} tick={{ fontSize: 11, fill: 'hsl(220, 10%, 50%)' }} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="critical" name="Critical" stackId="1" stroke="#ef4444" fill="url(#gradCrit)" />
                <Area type="monotone" dataKey="major"    name="Major"    stackId="1" stroke="#f59e0b" fill="url(#gradMaj)" />
                <Area type="monotone" dataKey="minor"    name="Minor"    stackId="1" stroke="#22c55e" fill="url(#gradMin)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 2. Severity Breakdown (Pie Chart) */}
        <div className={`${styles.chartCard} ${styles.chartCardSpan4}`}>
          <div className={styles.chartHeader}>
            <div>
              <h3 className={styles.chartTitle}>Severity Breakdown</h3>
              <p className={styles.chartSubtitle}>Distribution of complaint severity</p>
            </div>
          </div>
          <div className={styles.chartBody}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={severity_breakdown}
                  dataKey="count"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={55}
                  outerRadius={85}
                  paddingAngle={4}
                >
                  {severity_breakdown.map((entry) => (
                    <Cell key={entry.key} fill={SEVERITY_COLORS[entry.key] || '#94a3b8'} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 3. Top Products by Complaint Volume (Bar Chart) */}
        <div className={`${styles.chartCard} ${styles.chartCardSpan6}`}>
          <div className={styles.chartHeader}>
            <div>
              <h3 className={styles.chartTitle}>Top Affected Products</h3>
              <p className={styles.chartSubtitle}>Products with highest complaint volume</p>
            </div>
          </div>
          <div className={styles.chartBody}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={top_products} layout="vertical" margin={{ top: 5, right: 20, left: 40, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="hsl(220, 15%, 92%)" />
                <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
                <YAxis dataKey="product_name" type="category" width={110} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" name="Complaints" fill="hsl(220, 90%, 56%)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 4. Complaint Category Breakdown (Bar Chart) */}
        <div className={`${styles.chartCard} ${styles.chartCardSpan6}`}>
          <div className={styles.chartHeader}>
            <div>
              <h3 className={styles.chartTitle}>Category Distribution</h3>
              <p className={styles.chartSubtitle}>Defect categories reported</p>
            </div>
          </div>
          <div className={styles.chartBody}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={category_breakdown} margin={{ top: 15, right: 15, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(220, 15%, 92%)" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" name="Complaints" radius={[4, 4, 0, 0]}>
                  {category_breakdown.map((entry, index) => (
                    <Cell key={index} fill={CATEGORY_COLORS[index % CATEGORY_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>
    </div>
  );
}
