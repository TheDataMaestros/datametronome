import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Database, 
  Shield, 
  CheckCircle, 
  AlertTriangle, 
  TrendingUp, 
  Activity,
  Clock,
  Users,
  BarChart3,
  RefreshCw
} from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';

interface Stave {
  id: string;
  name: string;
  data_source_type: string;
  is_active: boolean;
  created_at: string;
}

interface Clef {
  id: string;
  name: string;
  stave_id: string;
  check_type: string;
  is_active: boolean;
  schedule: string;
}

interface CheckResult {
  id: string;
  clef_id: string;
  stave_id: string;
  status: 'pass' | 'fail' | 'warn';
  timestamp: string;
  execution_time: number;
  anomalies_count: number;
  message: string;
}

const Overview: React.FC = () => {
  const [staves, setStaves] = useState<Stave[]>([]);
  const [clefs, setClefs] = useState<Clef[]>([]);
  const [recentResults, setRecentResults] = useState<CheckResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const loadData = async () => {
    try {
      setIsLoading(true);
      
      // Load staves
      const stavesResponse = await axios.get('/staves/');
      setStaves(stavesResponse.data);

      // Load clefs
      const clefsResponse = await axios.get('/clefs/');
      setClefs(clefsResponse.data);

      // Load recent check results
      const allResults: CheckResult[] = [];
      for (const clef of clefsResponse.data) {
        try {
          const resultsResponse = await axios.get(`/clefs/${clef.id}/results`);
          const clefResults = resultsResponse.data.results || [];
          allResults.push(...clefResults.slice(0, 2)); // Get 2 most recent per clef
        } catch (error) {
          console.warn(`Could not load results for clef ${clef.id}`);
        }
      }
      
      // Sort by timestamp and take most recent
      allResults.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
      setRecentResults(allResults.slice(0, 10));

      setLastRefresh(new Date());
    } catch (error: any) {
      console.error('Error loading data:', error);
      toast.error('Failed to load dashboard data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Calculate metrics
  const totalStaves = staves.length;
  const activeStaves = staves.filter(s => s.is_active).length;
  const totalClefs = clefs.length;
  const activeClefs = clefs.filter(c => c.is_active).length;
  
  const totalChecks = recentResults.length;
  const passedChecks = recentResults.filter(r => r.status === 'pass').length;
  const failedChecks = recentResults.filter(r => r.status === 'fail').length;
  const warningChecks = recentResults.filter(r => r.status === 'warn').length;
  
  const successRate = totalChecks > 0 ? (passedChecks / totalChecks) * 100 : 100;

  // Chart data
  const statusData = [
    { name: 'Passed', value: passedChecks, color: '#22c55e' },
    { name: 'Failed', value: failedChecks, color: '#ef4444' },
    { name: 'Warning', value: warningChecks, color: '#f59e0b' },
  ];

  const performanceData = recentResults.slice(0, 7).map(result => ({
    time: new Date(result.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    executionTime: result.execution_time,
    status: result.status,
  }));

  const MetricCard: React.FC<{
    title: string;
    value: string | number;
    change?: string;
    icon: React.ReactNode;
    color: string;
    delay?: number;
  }> = ({ title, value, change, icon, color, delay = 0 }) => (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      className="metric-card"
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          {change && (
            <p className="text-sm text-gray-500">{change}</p>
          )}
        </div>
        <div className={`p-3 rounded-lg ${color}`}>
          {icon}
        </div>
      </div>
    </motion.div>
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-primary-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading dashboard data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard Overview</h1>
          <p className="text-gray-600 mt-1">
            Monitor your data quality metrics and system health
          </p>
        </div>
        <button
          onClick={loadData}
          className="btn-primary flex items-center"
          disabled={isLoading}
        >
          <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Success Rate"
          value={`${successRate.toFixed(1)}%`}
          change={`${passedChecks} of ${totalChecks} checks passed`}
          icon={<CheckCircle className="w-6 h-6 text-white" />}
          color="bg-success-500"
          delay={0}
        />
        
        <MetricCard
          title="Active Staves"
          value={`${activeStaves}/${totalStaves}`}
          change="Data sources"
          icon={<Database className="w-6 h-6 text-white" />}
          color="bg-primary-500"
          delay={0.1}
        />
        
        <MetricCard
          title="Active Clefs"
          value={`${activeClefs}/${totalClefs}`}
          change="Quality checks"
          icon={<Shield className="w-6 h-6 text-white" />}
          color="bg-secondary-500"
          delay={0.2}
        />
        
        <MetricCard
          title="Last Check"
          value={recentResults[0] ? 
            new Date(recentResults[0].timestamp).toLocaleTimeString() : 
            'No data'
          }
          change="Most recent execution"
          icon={<Clock className="w-6 h-6 text-white" />}
          color="bg-warning-500"
          delay={0.3}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Status Distribution */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="card"
        >
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Check Status Distribution</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={statusData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {statusData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center space-x-6 mt-4">
            {statusData.map((item) => (
              <div key={item.name} className="flex items-center">
                <div 
                  className="w-3 h-3 rounded-full mr-2" 
                  style={{ backgroundColor: item.color }}
                ></div>
                <span className="text-sm text-gray-600">{item.name}: {item.value}</span>
              </div>
            ))}
          </div>
        </motion.div>

        {/* Performance Trend */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.5 }}
          className="card"
        >
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Execution Performance</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={performanceData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Line 
                  type="monotone" 
                  dataKey="executionTime" 
                  stroke="#0ea5e9" 
                  strokeWidth={2}
                  dot={{ fill: '#0ea5e9', strokeWidth: 2, r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      </div>

      {/* Recent Activity */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.6 }}
        className="card"
      >
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h3>
        {recentResults.length > 0 ? (
          <div className="space-y-3">
            {recentResults.slice(0, 5).map((result) => (
              <div key={result.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center">
                  <div className={`w-2 h-2 rounded-full mr-3 ${
                    result.status === 'pass' ? 'bg-success-500' :
                    result.status === 'fail' ? 'bg-error-500' : 'bg-warning-500'
                  }`}></div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">
                      {clefs.find(c => c.id === result.clef_id)?.name || 'Unknown Clef'}
                    </p>
                    <p className="text-xs text-gray-500">
                      {staves.find(s => s.id === result.stave_id)?.name || 'Unknown Stave'}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-900">
                    {result.status === 'pass' ? '✅ Passed' :
                     result.status === 'fail' ? '❌ Failed' : '⚠️ Warning'}
                  </p>
                  <p className="text-xs text-gray-500">
                    {new Date(result.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <Activity className="w-12 h-12 mx-auto mb-4 text-gray-300" />
            <p>No recent activity found</p>
            <p className="text-sm">Run some checks to see activity here</p>
          </div>
        )}
      </motion.div>

      {/* Last Updated */}
      <div className="text-center text-sm text-gray-500">
        Last updated: {lastRefresh.toLocaleString()}
      </div>
    </div>
  );
};

export default Overview;
