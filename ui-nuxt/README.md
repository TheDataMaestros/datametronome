# DataMetronome UI - Nuxt Dashboard

A modern, responsive dashboard built with Nuxt 3 and Nuxt UI for the DataMetronome data quality monitoring platform.

## Features

- 🎨 **Modern Design**: Clean, professional interface inspired by the Nuxt dashboard template
- 📊 **Real-time Monitoring**: Live data quality metrics and anomaly detection
- 🤖 **ML Integration**: Machine learning powered anomaly detection with visualizations
- 📱 **Responsive**: Works perfectly on desktop, tablet, and mobile devices
- 🌙 **Dark Mode**: Built-in dark/light theme support
- ⚡ **Fast**: Optimized with Nuxt 3 and modern web technologies

## Tech Stack

- **Framework**: Nuxt 3
- **UI Library**: Nuxt UI
- **Styling**: Tailwind CSS
- **Charts**: Chart.js with Vue-ChartJS
- **State Management**: Pinia
- **TypeScript**: Full TypeScript support

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000) in your browser

### Demo Credentials

- **Username**: admin
- **Password**: admin

## Project Structure

```
ui-nuxt/
├── assets/
│   └── css/
│       └── main.css          # Custom styles and themes
├── layouts/
│   └── dashboard.vue         # Main dashboard layout
├── pages/
│   ├── index.vue            # Dashboard overview
│   ├── anomalies.vue        # Anomaly detection
│   ├── ml-anomalies.vue     # ML anomaly detection
│   └── login.vue            # Authentication
├── stores/
│   └── auth.ts              # Authentication store
├── app.vue                  # Root component
├── nuxt.config.ts           # Nuxt configuration
└── package.json             # Dependencies
```

## Pages Overview

### 🏠 Dashboard
- System health metrics
- Real-time charts and visualizations
- Recent activity feed
- Quick actions
- Data source status

### 🚨 Anomalies
- Data quality anomaly detection
- Severity-based filtering
- Detailed anomaly analysis
- Resolution tracking

### 🤖 ML Anomalies
- Machine learning powered detection
- Model configuration
- Confidence scoring
- Feature analysis

### 📈 Trends & Patterns
- Data distribution analysis
- Time series visualization
- Correlation analysis
- Pattern recognition

### 🔍 Investigation
- Custom SQL queries
- Data profiling
- Sample data viewer

### 📄 Reports
- Data quality summaries
- Anomaly reports
- Performance metrics
- Custom report generation

### ⚙️ Data Sources (Staves)
- Database connection management
- Connection testing
- Data preview
- Sample data generation

### 🎯 Quality Checks (Clefs)
- Data quality rule configuration
- Check scheduling
- Result monitoring
- Performance tracking

## API Integration

The UI communicates with the DataMetronome Podium API backend:

- **Base URL**: `http://localhost:8001/api/v1`
- **Authentication**: Bearer token
- **Endpoints**:
  - `/auth/login` - User authentication
  - `/staves/` - Data source management
  - `/clefs/` - Quality check management
  - `/anomalies/` - Anomaly detection results

## Customization

### Themes
The dashboard supports both light and dark themes. Customize colors in `assets/css/main.css`:

```css
:root {
  --datametronome-primary: #1f77b4;
  --datametronome-secondary: #ff6b6b;
  --datametronome-success: #2ed573;
  /* ... */
}
```

### Components
All components are built with Nuxt UI and can be customized using Tailwind CSS classes.

## Development

### Adding New Pages
1. Create a new `.vue` file in the `pages/` directory
2. The page will automatically be available at the corresponding route
3. Use the `dashboard` layout for consistent styling

### Adding New Components
1. Create components in the `components/` directory
2. Use Nuxt UI components as building blocks
3. Follow the established design patterns

### API Integration
1. Use `$fetch` for API calls
2. Handle authentication with the auth store
3. Implement proper error handling

## Deployment

### Build for Production
```bash
npm run build
```

### Preview Production Build
```bash
npm run preview
```

### Deploy
The built application can be deployed to any static hosting service or server that supports Node.js.

## Contributing

1. Follow the existing code style
2. Use TypeScript for type safety
3. Test your changes thoroughly
4. Update documentation as needed

## License

MIT License - see LICENSE file for details.
