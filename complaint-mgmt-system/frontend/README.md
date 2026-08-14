# 🎨 Frontend — CustomerHelperAI React Portal

> **Modern React 19 single-page application for pharmaceutical & medical complaint management, interactive AI copilot assistance, and real-time quality analytics.**

---

## 🚀 Overview

The frontend is built with **React 19**, **Vite**, and **Redux Toolkit**, providing a responsive and fluid interface for quality engineers, clinical investigators, and administrators.

### Core Features
- 🤖 **3D Animated Robot Copilot (`RobotAvatar.jsx`)**: Canvas-rendered interactive avatar with dynamic idle, thinking, and talking states.
- 📋 **Multi-Field Complaint Intake Form (`ComplaintForm.jsx`)**: 16+ structured fields with live bi-directional sync to the AI Copilot.
- 💬 **Copilot Chat & Field Auto-Population (`CopilotChat.jsx`)**: Chat interface that parses unstructured emails or reports into form values with one click.
- 📊 **Executive Quality Dashboard (`DashboardView.jsx`)**: Interactive Recharts analytics covering risk levels, product trends, defect types, and resolution times.
- 📑 **Complaint Management Table (`ComplaintsList.jsx`)**: Searchable, filterable, and paginated table with real-time status badges and detail drawers.

---

## 📁 Source Layout

```
src/
├── api/                     # RTK Query API client (axiosBaseQuery)
│   ├── baseQuery.js         # Axios base query with error handling
│   ├── complaintsApi.js     # RTK endpoints for complaints & documents
│   ├── copilotApi.js        # RTK endpoints for AI copilot chat & parsing
│   └── analyticsApi.js      # RTK endpoints for executive dashboard metrics
├── app/
│   └── store.js             # Central Redux store configuration
├── components/
│   └── RobotAvatar.jsx      # Canvas-based 3D robot avatar component
├── features/
│   ├── complaints/          # Form, list views, and complaint detail drawers
│   ├── copilot/             # Copilot chat panel and quick action handlers
│   └── dashboard/           # Analytics KPIs and Recharts charts
├── App.jsx                  # Main application router and state synchronization
├── main.jsx                 # React root mounting
└── index.css                # Global styles and modern theme design tokens
```

---

## 🛠 Available Scripts

In the frontend directory:

```bash
# Install dependencies
npm install

# Start Vite local development server with HMR
npm run dev

# Build production bundle with Vite
npm run build

# Preview production build locally
npm run preview

# Run Oxlint for fast static analysis
npx oxlint
```

---

## ⚙️ Environment Configuration

Create a `.env` file in the `frontend` folder:

```env
VITE_API_BASE_URL=http://localhost:8000
```
