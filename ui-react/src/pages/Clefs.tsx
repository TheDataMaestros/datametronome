import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Shield, 
  Plus, 
  Trash2, 
  Play, 
  Eye, 
  Settings,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Clock,
  BarChart3
} from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';

interface Stave {
  id: string;
  name: string;
  data_source_type: string;
}

interface Clef {
  id: string;
  name: string;
  description: string;
  stave_id: string;
  check_type: string;
  config: any;
  schedule: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
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
  metadata?: any;
}

const Clefs: React.FC = () => {
  const [staves, setStaves] = useState<Stave[]>([]);
  const [clefs, setClefs] = useState<Clef[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [selectedClef, setSelectedClef] = useState<Clef | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const loadData = async () => {
    try {
      setIsLoading(true);
      
      // Load staves
      const stavesResponse = await axios.get('/staves/');
      setStaves(stavesResponse.data);

      // Load clefs
      const clefsResponse = await axios.get('/clefs/');
      setClefs(clefsResponse.data);
    } catch (error: any) {
      console.error('Error loading data:', error);
      toast.error('Failed to load clefs data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateClef = async (formData: any) => {
    try {
      setIsCreating(true);
      const response = await axios.post('/clefs/', formData);
      toast.success(`Clef "${formData.name}" created successfully!`);
      setShowCreateForm(false);
      loadData();
    } catch (error: any) {
      console.error('Error creating clef:', error);
      toast.error('Failed to create clef');
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteClef = async (clefId: string, clefName: string) => {
    if (!window.confirm(`Are you sure you want to delete "${clefName}"?`)) {
      return;
    }

    try {
      await axios.delete(`/clefs/${clefId}`);
      toast.success(`Clef "${clefName}" deleted successfully!`);
      loadData();
    } catch (error: any) {
      console.error('Error deleting clef:', error);
      toast.error('Failed to delete clef');
    }
  };

  const handleRunClef = async (clefId: string) => {
    try {
      const response = await axios.post(`/clefs/${clefId}/run-now`);
      if (response.data.success) {
        const status = response.data.status;
        const statusIcon = status === 'pass' ? '✅' : status === 'fail' ? '❌' : '⚠️';
        toast.success(`${statusIcon} Check completed: ${response.data.message}`);
      } else {
        toast.error(`Check failed: ${response.data.message}`);
      }
    } catch (error: any) {
      console.error('Error running clef:', error);
      toast.error('Failed to run clef');
    }
  };

  const handleViewResults = async (clefId: string) => {
    try {
      const response = await axios.get(`/clefs/${clefId}/results`);
      const results = response.data.results || [];
      
      if (results.length > 0) {
        setSelectedClef({ 
          ...clefs.find(c => c.id === clefId)!, 
          results: results 
        });
        toast.success(`Loaded ${results.length} execution results`);
      } else {
        toast.info('No execution results found for this clef');
      }
    } catch (error: any) {
      console.error('Error loading results:', error);
      toast.error('Failed to load clef results');
    }
  };

  const getStatusIcon = (isActive: boolean) => {
    return isActive ? (
      <CheckCircle className="w-5 h-5 text-success-500" />
    ) : (
      <XCircle className="w-5 h-5 text-error-500" />
    );
  };

  const getCheckTypeIcon = (checkType: string) => {
    const iconMap: { [key: string]: React.ReactNode } = {
      'null_check': <AlertTriangle className="w-5 h-5 text-yellow-500" />,
      'range_check': <BarChart3 className="w-5 h-5 text-blue-500" />,
      'uniqueness_check': <Shield className="w-5 h-5 text-green-500" />,
      'schema_check': <Settings className="w-5 h-5 text-purple-500" />,
      'custom_sql': <Settings className="w-5 h-5 text-gray-500" />,
    };
    return iconMap[checkType] || <Shield className="w-5 h-5 text-gray-500" />;
  };

  const getStaveName = (staveId: string) => {
    return staves.find(s => s.id === staveId)?.name || 'Unknown Stave';
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-primary-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading clefs...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Quality Checks (Clefs)</h1>
          <p className="text-gray-600 mt-1">
            Manage your data quality checks and monitoring rules
          </p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={loadData}
            className="btn-secondary flex items-center"
            disabled={isLoading}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowCreateForm(true)}
            className="btn-primary flex items-center"
            disabled={staves.length === 0}
          >
            <Plus className="w-4 h-4 mr-2" />
            New Clef
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="metric-card"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Clefs</p>
              <p className="text-2xl font-bold text-gray-900">{clefs.length}</p>
            </div>
            <Shield className="w-8 h-8 text-primary-500" />
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
              <p className="text-sm font-medium text-gray-600">Active Clefs</p>
              <p className="text-2xl font-bold text-gray-900">
                {clefs.filter(c => c.is_active).length}
              </p>
            </div>
            <CheckCircle className="w-8 h-8 text-success-500" />
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
              <p className="text-sm font-medium text-gray-600">Scheduled Clefs</p>
              <p className="text-2xl font-bold text-gray-900">
                {clefs.filter(c => c.schedule).length}
              </p>
            </div>
            <Clock className="w-8 h-8 text-warning-500" />
          </div>
        </motion.div>
      </div>

      {/* Clefs List */}
      <div className="space-y-4">
        {clefs.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="card text-center py-12"
          >
            <Shield className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No clefs configured</h3>
            <p className="text-gray-600 mb-6">
              {staves.length === 0 
                ? 'Create a stave first, then create your first quality check'
                : 'Create your first data quality check to get started'
              }
            </p>
            {staves.length > 0 && (
              <button
                onClick={() => setShowCreateForm(true)}
                className="btn-primary flex items-center mx-auto"
              >
                <Plus className="w-4 h-4 mr-2" />
                Create First Clef
              </button>
            )}
          </motion.div>
        ) : (
          clefs.map((clef, index) => (
            <motion.div
              key={clef.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="card-hover"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  {getCheckTypeIcon(clef.check_type)}
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">{clef.name}</h3>
                    <p className="text-sm text-gray-600">{clef.description}</p>
                    <div className="flex items-center space-x-4 mt-2">
                      <span className="status-badge bg-gray-100 text-gray-800">
                        {clef.check_type.replace('_', ' ')}
                      </span>
                      <span className="status-badge bg-blue-100 text-blue-800">
                        {getStaveName(clef.stave_id)}
                      </span>
                      <div className="flex items-center">
                        {getStatusIcon(clef.is_active)}
                        <span className="ml-1 text-sm text-gray-600">
                          {clef.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                      {clef.schedule && (
                        <div className="flex items-center">
                          <Clock className="w-4 h-4 text-gray-400 mr-1" />
                          <span className="text-sm text-gray-600">{clef.schedule}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleRunClef(clef.id)}
                    className="p-2 text-gray-600 hover:text-success-600 hover:bg-success-50 rounded-lg"
                    title="Run Now"
                  >
                    <Play className="w-4 h-4" />
                  </button>
                  
                  <button
                    onClick={() => handleViewResults(clef.id)}
                    className="p-2 text-gray-600 hover:text-primary-600 hover:bg-primary-50 rounded-lg"
                    title="View Results"
                  >
                    <Eye className="w-4 h-4" />
                  </button>
                  
                  <button
                    onClick={() => setSelectedClef(clef)}
                    className="p-2 text-gray-600 hover:text-primary-600 hover:bg-primary-50 rounded-lg"
                    title="Settings"
                  >
                    <Settings className="w-4 h-4" />
                  </button>
                  
                  <button
                    onClick={() => handleDeleteClef(clef.id, clef.name)}
                    className="p-2 text-gray-600 hover:text-error-600 hover:bg-error-50 rounded-lg"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </motion.div>
          ))
        )}
      </div>

      {/* Create Clef Modal */}
      {showCreateForm && (
        <CreateClefModal
          staves={staves}
          onClose={() => setShowCreateForm(false)}
          onSubmit={handleCreateClef}
          isLoading={isCreating}
        />
      )}

      {/* Clef Details Modal */}
      {selectedClef && (
        <ClefDetailsModal
          clef={selectedClef}
          staveName={getStaveName(selectedClef.stave_id)}
          onClose={() => setSelectedClef(null)}
          onRunClef={handleRunClef}
        />
      )}
    </div>
  );
};

// Create Clef Modal Component
const CreateClefModal: React.FC<{
  staves: Stave[];
  onClose: () => void;
  onSubmit: (data: any) => void;
  isLoading: boolean;
}> = ({ staves, onClose, onSubmit, isLoading }) => {
  const [formData, setFormData] = useState({
    stave_id: '',
    name: '',
    description: '',
    check_type: 'null_check',
    schedule: '0 * * * *',
    config: {}
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const updateConfig = (newConfig: any) => {
    setFormData({ ...formData, config: newConfig });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white rounded-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto"
      >
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Create New Clef</h2>
        
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Stave
              </label>
              <select
                value={formData.stave_id}
                onChange={(e) => setFormData({ ...formData, stave_id: e.target.value })}
                className="input-field"
                required
              >
                <option value="">Select a stave</option>
                {staves.map(stave => (
                  <option key={stave.id} value={stave.id}>
                    {stave.name} ({stave.data_source_type})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Check Type
              </label>
              <select
                value={formData.check_type}
                onChange={(e) => setFormData({ ...formData, check_type: e.target.value })}
                className="input-field"
                required
              >
                <option value="null_check">Null Check</option>
                <option value="range_check">Range Check</option>
                <option value="uniqueness_check">Uniqueness Check</option>
                <option value="schema_check">Schema Check</option>
                <option value="custom_sql">Custom SQL</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Clef Name
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="input-field"
              placeholder="e.g., Check for NULL emails"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="input-field"
              rows={3}
              placeholder="Description of this quality check"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Schedule (Cron)
            </label>
            <input
              type="text"
              value={formData.schedule}
              onChange={(e) => setFormData({ ...formData, schedule: e.target.value })}
              className="input-field"
              placeholder="0 * * * *"
              required
            />
            <p className="text-sm text-gray-500 mt-1">
              Cron expression for scheduling (e.g., "0 * * * *" for hourly)
            </p>
          </div>

          {/* Dynamic Config based on check type */}
          <CheckConfigForm 
            checkType={formData.check_type} 
            config={formData.config}
            onConfigChange={updateConfig}
          />

          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary"
              disabled={isLoading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary flex items-center"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4 mr-2" />
                  Create Clef
                </>
              )}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
};

// Check Config Form Component
const CheckConfigForm: React.FC<{
  checkType: string;
  config: any;
  onConfigChange: (config: any) => void;
}> = ({ checkType, config, onConfigChange }) => {
  const updateConfig = (key: string, value: any) => {
    onConfigChange({ ...config, [key]: value });
  };

  switch (checkType) {
    case 'null_check':
      return (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Null Check Configuration</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Table
              </label>
              <input
                type="text"
                value={config.table || ''}
                onChange={(e) => updateConfig('table', e.target.value)}
                className="input-field"
                placeholder="users"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Column
              </label>
              <input
                type="text"
                value={config.column || ''}
                onChange={(e) => updateConfig('column', e.target.value)}
                className="input-field"
                placeholder="email"
                required
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Threshold (%)
              </label>
              <input
                type="number"
                value={config.threshold ? config.threshold * 100 : 1}
                onChange={(e) => updateConfig('threshold', parseFloat(e.target.value) / 100)}
                className="input-field"
                min="0"
                max="100"
                step="0.1"
                required
              />
            </div>
          </div>
        </div>
      );

    case 'range_check':
      return (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Range Check Configuration</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Table
              </label>
              <input
                type="text"
                value={config.table || ''}
                onChange={(e) => updateConfig('table', e.target.value)}
                className="input-field"
                placeholder="users"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Column
              </label>
              <input
                type="text"
                value={config.column || ''}
                onChange={(e) => updateConfig('column', e.target.value)}
                className="input-field"
                placeholder="age"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Min Value
              </label>
              <input
                type="number"
                value={config.min || 0}
                onChange={(e) => updateConfig('min', parseInt(e.target.value))}
                className="input-field"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Max Value
              </label>
              <input
                type="number"
                value={config.max || 120}
                onChange={(e) => updateConfig('max', parseInt(e.target.value))}
                className="input-field"
                required
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Threshold (%)
              </label>
              <input
                type="number"
                value={config.threshold ? config.threshold * 100 : 2}
                onChange={(e) => updateConfig('threshold', parseFloat(e.target.value) / 100)}
                className="input-field"
                min="0"
                max="100"
                step="0.1"
                required
              />
            </div>
          </div>
        </div>
      );

    case 'uniqueness_check':
      return (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Uniqueness Check Configuration</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Table
              </label>
              <input
                type="text"
                value={config.table || ''}
                onChange={(e) => updateConfig('table', e.target.value)}
                className="input-field"
                placeholder="users"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Column
              </label>
              <input
                type="text"
                value={config.column || ''}
                onChange={(e) => updateConfig('column', e.target.value)}
                className="input-field"
                placeholder="email"
                required
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Threshold (%)
              </label>
              <input
                type="number"
                value={config.threshold ? config.threshold * 100 : 0}
                onChange={(e) => updateConfig('threshold', parseFloat(e.target.value) / 100)}
                className="input-field"
                min="0"
                max="100"
                step="0.1"
                required
              />
            </div>
          </div>
        </div>
      );

    default:
      return (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Configuration</h3>
          <p className="text-gray-600">Configuration for {checkType} will be implemented.</p>
        </div>
      );
  }
};

// Clef Details Modal Component
const ClefDetailsModal: React.FC<{
  clef: Clef & { results?: CheckResult[] };
  staveName: string;
  onClose: () => void;
  onRunClef: (clefId: string) => void;
}> = ({ clef, staveName, onClose, onRunClef }) => {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white rounded-xl p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">{clef.name}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <XCircle className="w-6 h-6" />
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Clef Info */}
          <div className="space-y-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Clef Information</h3>
              <div className="space-y-2">
                <p><span className="font-medium">ID:</span> {clef.id}</p>
                <p><span className="font-medium">Type:</span> {clef.check_type.replace('_', ' ')}</p>
                <p><span className="font-medium">Stave:</span> {staveName}</p>
                <p><span className="font-medium">Schedule:</span> {clef.schedule}</p>
                <p><span className="font-medium">Status:</span> 
                  <span className={`ml-2 ${clef.is_active ? 'text-success-600' : 'text-error-600'}`}>
                    {clef.is_active ? 'Active' : 'Inactive'}
                  </span>
                </p>
                <p><span className="font-medium">Created:</span> {new Date(clef.created_at).toLocaleString()}</p>
              </div>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Configuration</h3>
              <div className="bg-gray-50 rounded-lg p-4">
                <pre className="text-sm text-gray-700">
                  {JSON.stringify(clef.config, null, 2)}
                </pre>
              </div>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Description</h3>
              <p className="text-gray-700">{clef.description}</p>
            </div>
          </div>

          {/* Actions and Results */}
          <div className="space-y-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Actions</h3>
              <div className="space-y-3">
                <button
                  onClick={() => onRunClef(clef.id)}
                  className="btn-success w-full flex items-center justify-center"
                >
                  <Play className="w-4 h-4 mr-2" />
                  Run Check Now
                </button>
              </div>
            </div>

            {/* Results */}
            {clef.results && (
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Recent Results</h3>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {clef.results.map((result) => (
                    <div key={result.id} className="bg-gray-50 rounded-lg p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center">
                          <div className={`w-2 h-2 rounded-full mr-3 ${
                            result.status === 'pass' ? 'bg-success-500' :
                            result.status === 'fail' ? 'bg-error-500' : 'bg-warning-500'
                          }`}></div>
                          <div>
                            <p className="text-sm font-medium text-gray-900">
                              {result.status === 'pass' ? '✅ Passed' :
                               result.status === 'fail' ? '❌ Failed' : '⚠️ Warning'}
                            </p>
                            <p className="text-xs text-gray-500">
                              {new Date(result.timestamp).toLocaleString()}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-sm text-gray-600">
                            {result.execution_time?.toFixed(3)}s
                          </p>
                          {result.anomalies_count > 0 && (
                            <p className="text-xs text-error-600">
                              {result.anomalies_count} anomalies
                            </p>
                          )}
                        </div>
                      </div>
                      {result.message && (
                        <p className="text-xs text-gray-600 mt-2">{result.message}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default Clefs;
