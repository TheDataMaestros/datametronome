import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Database, 
  Plus, 
  Trash2, 
  Play, 
  Eye, 
  Settings,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Download,
  Upload
} from 'lucide-react';
import axios from 'axios';
import toast from 'react-hot-toast';

interface Stave {
  id: string;
  name: string;
  description: string;
  data_source_type: string;
  connection_config: any;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

const Staves: React.FC = () => {
  const [staves, setStaves] = useState<Stave[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [selectedStave, setSelectedStave] = useState<Stave | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const loadStaves = async () => {
    try {
      setIsLoading(true);
      const response = await axios.get('/staves/');
      setStaves(response.data);
    } catch (error: any) {
      console.error('Error loading staves:', error);
      toast.error('Failed to load staves');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadStaves();
  }, []);

  const handleCreateStave = async (formData: any) => {
    try {
      setIsCreating(true);
      const response = await axios.post('/staves/', formData);
      toast.success(`Stave "${formData.name}" created successfully!`);
      setShowCreateForm(false);
      loadStaves();
    } catch (error: any) {
      console.error('Error creating stave:', error);
      toast.error('Failed to create stave');
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteStave = async (staveId: string, staveName: string) => {
    if (!window.confirm(`Are you sure you want to delete "${staveName}"?`)) {
      return;
    }

    try {
      await axios.delete(`/staves/${staveId}`);
      toast.success(`Stave "${staveName}" deleted successfully!`);
      loadStaves();
    } catch (error: any) {
      console.error('Error deleting stave:', error);
      toast.error('Failed to delete stave');
    }
  };

  const handleTestConnection = async (staveId: string) => {
    try {
      const response = await axios.post(`/stave-actions/${staveId}/test-connection`);
      if (response.data.success) {
        toast.success('Connection test successful!');
      } else {
        toast.error(`Connection test failed: ${response.data.message}`);
      }
    } catch (error: any) {
      console.error('Error testing connection:', error);
      toast.error('Connection test failed');
    }
  };

  const handlePreviewData = async (staveId: string, tableName: string = 'users') => {
    try {
      const response = await axios.post(`/stave-actions/${staveId}/preview-data`, {
        table_name: tableName,
        count: 10
      });
      
      if (response.data.success) {
        setSelectedStave({ ...staves.find(s => s.id === staveId)!, previewData: response.data.data });
        toast.success(`Preview loaded for ${tableName} table`);
      } else {
        toast.error(`Failed to preview data: ${response.data.message}`);
      }
    } catch (error: any) {
      console.error('Error previewing data:', error);
      toast.error('Failed to preview data');
    }
  };

  const handleGenerateData = async (staveId: string, tableName: string, count: number) => {
    try {
      const response = await axios.post(`/stave-actions/${staveId}/generate-data`, {
        table_name: tableName,
        count: count
      });
      
      if (response.data.success) {
        toast.success(`Generated ${count} records for ${tableName} table`);
      } else {
        toast.error(`Failed to generate data: ${response.data.message}`);
      }
    } catch (error: any) {
      console.error('Error generating data:', error);
      toast.error('Failed to generate data');
    }
  };

  const getStatusIcon = (isActive: boolean) => {
    return isActive ? (
      <CheckCircle className="w-5 h-5 text-success-500" />
    ) : (
      <XCircle className="w-5 h-5 text-error-500" />
    );
  };

  const getTypeIcon = (type: string) => {
    const iconMap: { [key: string]: React.ReactNode } = {
      'postgres': <Database className="w-5 h-5 text-blue-500" />,
      'sqlite': <Database className="w-5 h-5 text-green-500" />,
      'mysql': <Database className="w-5 h-5 text-orange-500" />,
      'bigquery': <Database className="w-5 h-5 text-purple-500" />,
      'snowflake': <Database className="w-5 h-5 text-blue-600" />,
    };
    return iconMap[type] || <Database className="w-5 h-5 text-gray-500" />;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-primary-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading staves...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Data Sources (Staves)</h1>
          <p className="text-gray-600 mt-1">
            Manage your data source connections and configurations
          </p>
        </div>
        <div className="flex space-x-3">
          <button
            onClick={loadStaves}
            className="btn-secondary flex items-center"
            disabled={isLoading}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowCreateForm(true)}
            className="btn-primary flex items-center"
          >
            <Plus className="w-4 h-4 mr-2" />
            New Stave
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
              <p className="text-sm font-medium text-gray-600">Total Staves</p>
              <p className="text-2xl font-bold text-gray-900">{staves.length}</p>
            </div>
            <Database className="w-8 h-8 text-primary-500" />
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
              <p className="text-sm font-medium text-gray-600">Active Staves</p>
              <p className="text-2xl font-bold text-gray-900">
                {staves.filter(s => s.is_active).length}
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
              <p className="text-sm font-medium text-gray-600">Inactive Staves</p>
              <p className="text-2xl font-bold text-gray-900">
                {staves.filter(s => !s.is_active).length}
              </p>
            </div>
            <XCircle className="w-8 h-8 text-error-500" />
          </div>
        </motion.div>
      </div>

      {/* Staves List */}
      <div className="space-y-4">
        {staves.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="card text-center py-12"
          >
            <Database className="w-16 h-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No staves configured</h3>
            <p className="text-gray-600 mb-6">Create your first data source to get started</p>
            <button
              onClick={() => setShowCreateForm(true)}
              className="btn-primary flex items-center mx-auto"
            >
              <Plus className="w-4 h-4 mr-2" />
              Create First Stave
            </button>
          </motion.div>
        ) : (
          staves.map((stave, index) => (
            <motion.div
              key={stave.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="card-hover"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  {getTypeIcon(stave.data_source_type)}
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">{stave.name}</h3>
                    <p className="text-sm text-gray-600">{stave.description}</p>
                    <div className="flex items-center space-x-4 mt-2">
                      <span className="status-badge bg-gray-100 text-gray-800">
                        {stave.data_source_type}
                      </span>
                      <div className="flex items-center">
                        {getStatusIcon(stave.is_active)}
                        <span className="ml-1 text-sm text-gray-600">
                          {stave.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleTestConnection(stave.id)}
                    className="p-2 text-gray-600 hover:text-primary-600 hover:bg-primary-50 rounded-lg"
                    title="Test Connection"
                  >
                    <Play className="w-4 h-4" />
                  </button>
                  
                  <button
                    onClick={() => handlePreviewData(stave.id)}
                    className="p-2 text-gray-600 hover:text-primary-600 hover:bg-primary-50 rounded-lg"
                    title="Preview Data"
                  >
                    <Eye className="w-4 h-4" />
                  </button>
                  
                  <button
                    onClick={() => setSelectedStave(stave)}
                    className="p-2 text-gray-600 hover:text-primary-600 hover:bg-primary-50 rounded-lg"
                    title="Settings"
                  >
                    <Settings className="w-4 h-4" />
                  </button>
                  
                  <button
                    onClick={() => handleDeleteStave(stave.id, stave.name)}
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

      {/* Create Stave Modal */}
      {showCreateForm && (
        <CreateStaveModal
          onClose={() => setShowCreateForm(false)}
          onSubmit={handleCreateStave}
          isLoading={isCreating}
        />
      )}

      {/* Stave Details Modal */}
      {selectedStave && (
        <StaveDetailsModal
          stave={selectedStave}
          onClose={() => setSelectedStave(null)}
          onPreviewData={handlePreviewData}
          onGenerateData={handleGenerateData}
        />
      )}
    </div>
  );
};

// Create Stave Modal Component
const CreateStaveModal: React.FC<{
  onClose: () => void;
  onSubmit: (data: any) => void;
  isLoading: boolean;
}> = ({ onClose, onSubmit, isLoading }) => {
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    data_source_type: 'postgres',
    connection_config: {
      host: 'localhost',
      port: 5432,
      database: '',
      user: '',
      password: ''
    }
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white rounded-xl p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto"
      >
        <h2 className="text-2xl font-bold text-gray-900 mb-6">Create New Stave</h2>
        
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Stave Name
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="input-field"
                placeholder="e.g., Production Database"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Data Source Type
              </label>
              <select
                value={formData.data_source_type}
                onChange={(e) => setFormData({ ...formData, data_source_type: e.target.value })}
                className="input-field"
              >
                <option value="postgres">PostgreSQL</option>
                <option value="sqlite">SQLite</option>
                <option value="mysql">MySQL</option>
                <option value="bigquery">BigQuery</option>
                <option value="snowflake">Snowflake</option>
              </select>
            </div>
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
              placeholder="Description of this data source"
              required
            />
          </div>

          {/* Connection Config */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Connection Configuration</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Host
                </label>
                <input
                  type="text"
                  value={formData.connection_config.host}
                  onChange={(e) => setFormData({
                    ...formData,
                    connection_config: { ...formData.connection_config, host: e.target.value }
                  })}
                  className="input-field"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Port
                </label>
                <input
                  type="number"
                  value={formData.connection_config.port}
                  onChange={(e) => setFormData({
                    ...formData,
                    connection_config: { ...formData.connection_config, port: parseInt(e.target.value) }
                  })}
                  className="input-field"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Database
                </label>
                <input
                  type="text"
                  value={formData.connection_config.database}
                  onChange={(e) => setFormData({
                    ...formData,
                    connection_config: { ...formData.connection_config, database: e.target.value }
                  })}
                  className="input-field"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Username
                </label>
                <input
                  type="text"
                  value={formData.connection_config.user}
                  onChange={(e) => setFormData({
                    ...formData,
                    connection_config: { ...formData.connection_config, user: e.target.value }
                  })}
                  className="input-field"
                  required
                />
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Password
                </label>
                <input
                  type="password"
                  value={formData.connection_config.password}
                  onChange={(e) => setFormData({
                    ...formData,
                    connection_config: { ...formData.connection_config, password: e.target.value }
                  })}
                  className="input-field"
                  required
                />
              </div>
            </div>
          </div>

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
                  Create Stave
                </>
              )}
            </button>
          </div>
        </form>
      </motion.div>
    </div>
  );
};

// Stave Details Modal Component
const StaveDetailsModal: React.FC<{
  stave: Stave & { previewData?: any[] };
  onClose: () => void;
  onPreviewData: (staveId: string, tableName?: string) => void;
  onGenerateData: (staveId: string, tableName: string, count: number) => void;
}> = ({ stave, onClose, onPreviewData, onGenerateData }) => {
  const [selectedTable, setSelectedTable] = useState('users');
  const [generateCount, setGenerateCount] = useState(50);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="bg-white rounded-xl p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto"
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-gray-900">{stave.name}</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <XCircle className="w-6 h-6" />
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Stave Info */}
          <div className="space-y-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Stave Information</h3>
              <div className="space-y-2">
                <p><span className="font-medium">ID:</span> {stave.id}</p>
                <p><span className="font-medium">Type:</span> {stave.data_source_type}</p>
                <p><span className="font-medium">Status:</span> 
                  <span className={`ml-2 ${stave.is_active ? 'text-success-600' : 'text-error-600'}`}>
                    {stave.is_active ? 'Active' : 'Inactive'}
                  </span>
                </p>
                <p><span className="font-medium">Created:</span> {new Date(stave.created_at).toLocaleString()}</p>
              </div>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Connection Config</h3>
              <div className="bg-gray-50 rounded-lg p-4">
                <pre className="text-sm text-gray-700">
                  {JSON.stringify(stave.connection_config, null, 2)}
                </pre>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="space-y-4">
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Data Preview</h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Table Name
                  </label>
                  <select
                    value={selectedTable}
                    onChange={(e) => setSelectedTable(e.target.value)}
                    className="input-field"
                  >
                    <option value="users">users</option>
                    <option value="orders">orders</option>
                    <option value="products">products</option>
                    <option value="events">events</option>
                  </select>
                </div>
                <button
                  onClick={() => onPreviewData(stave.id, selectedTable)}
                  className="btn-primary w-full flex items-center justify-center"
                >
                  <Eye className="w-4 h-4 mr-2" />
                  Preview Data
                </button>
              </div>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Generate Sample Data</h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Number of Records
                  </label>
                  <input
                    type="number"
                    value={generateCount}
                    onChange={(e) => setGenerateCount(parseInt(e.target.value))}
                    className="input-field"
                    min="1"
                    max="1000"
                  />
                </div>
                <button
                  onClick={() => onGenerateData(stave.id, selectedTable, generateCount)}
                  className="btn-success w-full flex items-center justify-center"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Generate Data
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Preview Data Display */}
        {stave.previewData && (
          <div className="mt-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Preview Data</h3>
            <div className="bg-gray-50 rounded-lg p-4 max-h-64 overflow-y-auto">
              <pre className="text-sm text-gray-700">
                {JSON.stringify(stave.previewData, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  );
};

export default Staves;
