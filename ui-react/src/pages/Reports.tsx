import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  FileText, 
  Download, 
  Calendar,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Clock,
  BarChart3,
  RefreshCw
} from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';

interface ReportData {
  summary: {
    total_staves: number;
    active_staves: number;
    total_clefs: number;
    active_clefs: number;
    total_checks: number;
    passed_checks: number;
    failed_checks: number;
    warning_checks: number;
    success_rate: number;
  };
  trends: Array<{
    date: string;
    checks_run: number;
    success_rate: number;
    anomalies_detected: number;
  }>;
  anomalies: Array<{
    id: string;
    clef_name: string;
    stave_name: string;
    severity: string;
    detected_at: string;
    message: string;
  }>;
}

const Reports: React.FC = () => {
  const [reportData, setReportData] = useState<ReportData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedPeriod, setSelectedPeriod] = useState('7');
  const [reportType, setReportType] = useState('summary');

  const loadReportData = async () => {
    try {
      setIsLoading(true);
      
      // Load summary report
      const summaryResponse = await axios.get('/reports/summary');
      const summary = summaryResponse.data;

      // Load quality report for trends
      const qualityResponse = await axios.get(`/reports/quality?days=${selectedPeriod}`);
      const quality = qualityResponse.data;

      // Mock trends data (in real app, this would come from API)
      const trends = generateMockTrends(parseInt(selectedPeriod));

      // Mock anomalies data
      const anomalies = generateMockAnomalies();

      setReportData({
        summary,
        trends,
        anomalies
      });
    } catch (error: any) {
      console.error('Error loading report data:', error);
      toast.error('Failed to load report data');
    } finally {
      setIsLoading(false);
    }
  };

  const generateMockTrends = (days: number) => {
    const trends = [];
    const now = new Date();
    
    for (let i = days - 1; i >= 0; i--) {
      const date = new Date(now);
      date.setDate(date.getDate() - i);
      
      trends.push({
        date: date.toISOString().split('T')[0],
        checks_run: Math.floor(Math.random() * 50) + 20,
        success_rate: Math.random() * 20 + 80, // 80-100%
        anomalies_detected: Math.floor(Math.random() * 10)
      });
    }
    
    return trends;
  };

  const generateMockAnomalies = () => {
    return [
      {
        id: '1',
        clef_name: 'Email Null Check',
        stave_name: 'Users Database',
        severity: 'High',
        detected_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
        message: 'Null email rate exceeded threshold (5.2% > 1%)'
      },
      {
        id: '2',
        clef_name: 'Age Range Check',
        stave_name: 'Users Database',
        severity: 'Medium',
        detected_at: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
        message: 'Age values outside expected range detected'
      },
      {
        id: '3',
        clef_name: 'Order Amount Check',
        stave_name: 'Orders Database',
        severity: 'Low',
        detected_at: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
        message: 'Unusual order amount pattern detected'
      }
    ];
  };

  useEffect(() => {
    loadReportData();
  }, [selectedPeriod]);

  const handleDownloadReport = (type: string) => {
    if (!reportData) return;

    let data: any;
    let filename: string;
    let mimeType: string;

    switch (type) {
      case 'summary':
        data = reportData.summary;
        filename = `datametronome-summary-${new Date().toISOString().split('T')[0]}.json`;
        mimeType = 'application/json';
        break;
      case 'anomalies':
        data = reportData.anomalies;
        filename = `datametronome-anomalies-${new Date().toISOString().split('T')[0]}.json`;
        mimeType = 'application/json';
        break;
      case 'trends':
        data = reportData.trends;
        filename = `datametronome-trends-${new Date().toISOString().split('T')[0]}.json`;
        mimeType = 'application/json';
        break;
      default:
        return;
    }

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    toast.success(`Report downloaded: ${filename}`);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-primary-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading reports...</p>
        </div>
      </div>
    );
  }

  if (!reportData) {
    return (
      <div className="text-center py-12">
        <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">No report data available</h3>
        <p className="text-gray-600">Try refreshing or check your API connection</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Reports & Analytics</h1>
          <p className="text-gray-600 mt-1">
            Comprehensive data quality reports and insights
          </p>
        </div>
        <div className="flex space-x-3">
          <select
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(e.target.value)}
            className="input-field"
          >
            <option value="1">Last 24 hours</option>
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
            <option value="90">Last 90 days</option>
          </select>
          <button
            onClick={loadReportData}
            className="btn-secondary flex items-center"
            disabled={isLoading}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Report Type Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'summary', name: 'Summary', icon: BarChart3 },
            { id: 'trends', name: 'Trends', icon: TrendingUp },
            { id: 'anomalies', name: 'Anomalies', icon: AlertTriangle },
          ].map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setReportType(tab.id)}
                className={`flex items-center py-2 px-1 border-b-2 font-medium text-sm ${
                  reportType === tab.id
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className="w-4 h-4 mr-2" />
                {tab.name}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Summary Report */}
      {reportType === 'summary' && (
        <div className="space-y-6">
          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="metric-card"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Success Rate</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {reportData.summary.success_rate.toFixed(1)}%
                  </p>
                </div>
                <CheckCircle className="w-8 h-8 text-success-500" />
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="metric-card"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Checks</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {reportData.summary.total_checks}
                  </p>
                </div>
                <BarChart3 className="w-8 h-8 text-primary-500" />
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="metric-card"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Active Staves</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {reportData.summary.active_staves}/{reportData.summary.total_staves}
                  </p>
                </div>
                <CheckCircle className="w-8 h-8 text-blue-500" />
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="metric-card"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Active Clefs</p>
                  <p className="text-2xl font-bold text-gray-900">
                    {reportData.summary.active_clefs}/{reportData.summary.total_clefs}
                  </p>
                </div>
                <AlertTriangle className="w-8 h-8 text-warning-500" />
              </div>
            </motion.div>
          </div>

          {/* Detailed Summary */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="card"
          >
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-gray-900">System Summary</h3>
              <button
                onClick={() => handleDownloadReport('summary')}
                className="btn-secondary flex items-center"
              >
                <Download className="w-4 h-4 mr-2" />
                Download
              </button>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="font-medium text-gray-900 mb-3">Check Results</h4>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Passed:</span>
                    <span className="font-medium text-success-600">{reportData.summary.passed_checks}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Failed:</span>
                    <span className="font-medium text-error-600">{reportData.summary.failed_checks}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Warnings:</span>
                    <span className="font-medium text-warning-600">{reportData.summary.warning_checks}</span>
                  </div>
                </div>
              </div>
              
              <div>
                <h4 className="font-medium text-gray-900 mb-3">System Health</h4>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Data Sources:</span>
                    <span className="font-medium">{reportData.summary.total_staves}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Quality Checks:</span>
                    <span className="font-medium">{reportData.summary.total_clefs}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Overall Health:</span>
                    <span className={`font-medium ${
                      reportData.summary.success_rate >= 95 ? 'text-success-600' :
                      reportData.summary.success_rate >= 85 ? 'text-warning-600' : 'text-error-600'
                    }`}>
                      {reportData.summary.success_rate >= 95 ? 'Excellent' :
                       reportData.summary.success_rate >= 85 ? 'Good' : 'Needs Attention'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      )}

      {/* Trends Report */}
      {reportType === 'trends' && (
        <div className="space-y-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="card"
          >
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-gray-900">Success Rate Trend</h3>
              <button
                onClick={() => handleDownloadReport('trends')}
                className="btn-secondary flex items-center"
              >
                <Download className="w-4 h-4 mr-2" />
                Download
              </button>
            </div>
            
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={reportData.trends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Line 
                    type="monotone" 
                    dataKey="success_rate" 
                    stroke="#0ea5e9" 
                    strokeWidth={2}
                    dot={{ fill: '#0ea5e9', strokeWidth: 2, r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </motion.div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="card"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Checks Run</h3>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={reportData.trends}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="checks_run" fill="#22c55e" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="card"
            >
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Anomalies Detected</h3>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={reportData.trends}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="anomalies_detected" fill="#ef4444" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </motion.div>
          </div>
        </div>
      )}

      {/* Anomalies Report */}
      {reportType === 'anomalies' && (
        <div className="space-y-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="card"
          >
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-gray-900">Recent Anomalies</h3>
              <button
                onClick={() => handleDownloadReport('anomalies')}
                className="btn-secondary flex items-center"
              >
                <Download className="w-4 h-4 mr-2" />
                Download
              </button>
            </div>
            
            <div className="space-y-4">
              {reportData.anomalies.map((anomaly, index) => (
                <motion.div
                  key={anomaly.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="border border-gray-200 rounded-lg p-4"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-3">
                      <div className={`w-2 h-2 rounded-full mt-2 ${
                        anomaly.severity === 'High' ? 'bg-error-500' :
                        anomaly.severity === 'Medium' ? 'bg-warning-500' : 'bg-blue-500'
                      }`}></div>
                      <div>
                        <h4 className="font-medium text-gray-900">{anomaly.clef_name}</h4>
                        <p className="text-sm text-gray-600">{anomaly.stave_name}</p>
                        <p className="text-sm text-gray-700 mt-1">{anomaly.message}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`status-badge ${
                        anomaly.severity === 'High' ? 'status-error' :
                        anomaly.severity === 'Medium' ? 'status-warning' : 'status-info'
                      }`}>
                        {anomaly.severity}
                      </span>
                      <p className="text-xs text-gray-500 mt-1">
                        {new Date(anomaly.detected_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
};

export default Reports;
