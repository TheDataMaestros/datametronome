# DataMetronome React Dashboard

A beautiful, modern React TypeScript dashboard for DataMetronome - your data quality monitoring platform.

## 🚀 Features

- **Beautiful UI**: Modern, responsive design with Tailwind CSS and Framer Motion animations
- **Authentication**: Secure login system with JWT tokens
- **Real-time Data**: Live connection to Podium API for staves and clefs management
- **Interactive Charts**: Beautiful data visualizations with Recharts
- **Responsive Design**: Works perfectly on desktop, tablet, and mobile
- **Dark/Light Theme**: Automatic theme detection with beautiful gradients

## 🎨 UI Components

- **Login Page**: Stunning gradient login with demo credentials
- **Dashboard Overview**: Real-time metrics, charts, and system health
- **Staves Management**: Create, configure, and manage data sources
- **Clefs Management**: Set up and monitor data quality checks
- **Reports & Analytics**: Comprehensive reporting with downloadable data

## 🛠️ Tech Stack

- **React 18** with TypeScript
- **Tailwind CSS** for styling
- **Framer Motion** for animations
- **Recharts** for data visualization
- **Axios** for API communication
- **React Router** for navigation
- **React Hot Toast** for notifications

## 🚀 Quick Start

### Prerequisites

- Node.js 16+ and npm
- DataMetronome Podium API running on port 8001

### Installation

1. **Install dependencies:**
   ```bash
   cd ui-react
   npm install
   ```

2. **Start the development server:**
   ```bash
   npm start
   ```

3. **Open your browser:**
   Navigate to [http://localhost:3000](http://localhost:3000)

### Demo Credentials

- **Username**: `admin`
- **Password**: `admin`

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the `ui-react` directory:

```env
REACT_APP_API_URL=http://localhost:8001
```

### API Connection

The dashboard connects to the Podium API by default on `http://localhost:8001`. Make sure your Podium API is running before starting the dashboard.

## 📱 Pages Overview

### 1. Login Page
- Beautiful gradient background
- Demo credentials display
- Responsive design
- Connection status indicators

### 2. Dashboard Overview
- **System Metrics**: Success rate, active staves/clefs, last check time
- **Interactive Charts**: Status distribution pie chart, execution performance trends
- **Recent Activity**: Live feed of check results
- **Real-time Updates**: Auto-refresh with manual refresh option

### 3. Staves Management
- **Create Staves**: Full form with connection configuration
- **Test Connections**: One-click connection testing
- **Data Preview**: Preview table data with customizable limits
- **Generate Sample Data**: Create test data for development
- **CRUD Operations**: Create, read, update, delete staves

### 4. Clefs Management
- **Create Clefs**: Multiple check types (null, range, uniqueness, schema, custom SQL)
- **Dynamic Configuration**: Forms adapt based on check type
- **Run Checks**: Execute checks manually
- **View Results**: Detailed execution history and results
- **Schedule Management**: Cron-based scheduling

### 5. Reports & Analytics
- **Summary Reports**: System health and metrics
- **Trend Analysis**: Success rate and performance trends over time
- **Anomaly Reports**: Detailed anomaly detection results
- **Downloadable Data**: Export reports in JSON format
- **Time Period Selection**: 24h, 7d, 30d, 90d views

## 🎨 Design Features

### Color Scheme
- **Primary**: Blue gradient (#0ea5e9 to #0284c7)
- **Secondary**: Purple gradient (#d946ef to #c026d3)
- **Success**: Green (#22c55e)
- **Warning**: Orange (#f59e0b)
- **Error**: Red (#ef4444)

### Animations
- **Fade In**: Smooth page transitions
- **Slide Up**: Card entrance animations
- **Hover Effects**: Interactive button and card states
- **Loading States**: Beautiful spinners and progress indicators

### Typography
- **Primary Font**: Inter (clean, modern)
- **Monospace**: JetBrains Mono (for code/config)

## 🔌 API Integration

The dashboard integrates with the following Podium API endpoints:

### Authentication
- `POST /api/v1/auth/login` - User authentication

### Staves (Data Sources)
- `GET /api/v1/staves/` - List all staves
- `POST /api/v1/staves/` - Create new stave
- `DELETE /api/v1/staves/{id}` - Delete stave
- `POST /api/v1/stave-actions/{id}/test-connection` - Test connection
- `POST /api/v1/stave-actions/{id}/preview-data` - Preview data
- `POST /api/v1/stave-actions/{id}/generate-data` - Generate sample data

### Clefs (Quality Checks)
- `GET /api/v1/clefs/` - List all clefs
- `POST /api/v1/clefs/` - Create new clef
- `DELETE /api/v1/clefs/{id}` - Delete clef
- `POST /api/v1/clefs/{id}/run-now` - Run check immediately
- `GET /api/v1/clefs/{id}/results` - Get check results

### Reports
- `GET /api/v1/reports/summary` - System summary
- `GET /api/v1/reports/quality` - Quality metrics

## 🚀 Deployment

### Production Build

```bash
npm run build
```

This creates a `build` folder with optimized production files.

### Docker Deployment

```dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 🎯 Key Features

### Real-time Updates
- Live data refresh from Podium API
- Automatic error handling and retry logic
- Connection status indicators

### User Experience
- Intuitive navigation with sidebar
- Responsive design for all screen sizes
- Loading states and error handling
- Toast notifications for user feedback

### Data Visualization
- Interactive charts with Recharts
- Real-time metrics display
- Trend analysis over time
- Status distribution visualization

### Security
- JWT token-based authentication
- Secure API communication
- Token storage in localStorage
- Automatic logout on token expiry

## 🛠️ Development

### Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── LoadingSpinner.tsx
│   └── Sidebar.tsx
├── contexts/            # React contexts
│   └── AuthContext.tsx
├── pages/               # Page components
│   ├── LoginPage.tsx
│   ├── Dashboard.tsx
│   ├── Overview.tsx
│   ├── Staves.tsx
│   ├── Clefs.tsx
│   └── Reports.tsx
├── App.tsx              # Main app component
├── index.tsx            # App entry point
└── index.css           # Global styles
```

### Available Scripts

- `npm start` - Start development server
- `npm run build` - Build for production
- `npm test` - Run tests
- `npm run eject` - Eject from Create React App

## 🎨 Customization

### Themes
The dashboard uses CSS custom properties for easy theming. Modify the color values in `tailwind.config.js` to change the color scheme.

### Components
All components are modular and can be easily customized or extended. The design system is consistent throughout the application.

## 📊 Performance

- **Bundle Size**: Optimized with code splitting
- **Loading**: Lazy loading for better performance
- **Caching**: API response caching where appropriate
- **Animations**: Hardware-accelerated animations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is part of the DataMetronome platform. See the main project license for details.

---

**Built with ❤️ for data quality monitoring**
