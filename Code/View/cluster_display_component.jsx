import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Check, Edit2, FolderOpen, Settings, ChevronRight, ChevronDown } from 'lucide-react';

const ClusterManagement = ({ initialData, onUpdateData }) => {
  const [clusters, setClusters] = useState({});
  const [expandedClusters, setExpandedClusters] = useState({});
  const [editingDocTypes, setEditingDocTypes] = useState({});
  const [selectedFiles, setSelectedFiles] = useState([]);

  useEffect(() => {
    // Group data by cluster
    const groupedData = initialData.reduce((acc, doc) => {
      const cluster = doc.cluster;
      if (!acc[cluster]) {
        acc[cluster] = {
          docType: doc.doc_type,
          isIndependent: doc.process_instance_independent,
          files: []
        };
      }
      acc[cluster].files.push(doc);
      return acc;
    }, {});
    setClusters(groupedData);
  }, [initialData]);

  const toggleClusterExpansion = (clusterId) => {
    setExpandedClusters(prev => ({
      ...prev,
      [clusterId]: !prev[clusterId]
    }));
  };

  const toggleDocTypeEdit = (clusterId) => {
    setEditingDocTypes(prev => ({
      ...prev,
      [clusterId]: !prev[clusterId]
    }));
  };

  const handleDocTypeChange = (clusterId, newDocType) => {
    setClusters(prev => ({
      ...prev,
      [clusterId]: {
        ...prev[clusterId],
        docType: newDocType
      }
    }));
    toggleDocTypeEdit(clusterId);
    // Update parent component
    onUpdateData(clusterId, { docType: newDocType });
  };

  const toggleFileSelection = (clusterId, fileName) => {
    setSelectedFiles(prev => {
      const fileKey = `${clusterId}-${fileName}`;
      if (prev.includes(fileKey)) {
        return prev.filter(f => f !== fileKey);
      }
      return [...prev, fileKey];
    });
  };

  const toggleIndependentStatus = (clusterId) => {
    setClusters(prev => ({
      ...prev,
      [clusterId]: {
        ...prev[clusterId],
        isIndependent: !prev[clusterId].isIndependent
      }
    }));
    // Update parent component
    onUpdateData(clusterId, { isIndependent: !clusters[clusterId].isIndependent });
  };

  return (
    <div className="space-y-4 p-4">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Cluster-Verwaltung</h2>
        <Button variant="outline" className="flex items-center gap-2">
          <Settings className="w-4 h-4" />
          Stapelaktionen
        </Button>
      </div>

      {Object.entries(clusters).map(([clusterId, clusterData]) => (
        <Card key={clusterId} className="p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-4">
              <button 
                onClick={() => toggleClusterExpansion(clusterId)}
                className="text-gray-500 hover:text-gray-700"
              >
                {expandedClusters[clusterId] ? 
                  <ChevronDown className="w-5 h-5" /> : 
                  <ChevronRight className="w-5 h-5" />
                }
              </button>
              
              <FolderOpen className="w-5 h-5 text-blue-500" />
              
              {editingDocTypes[clusterId] ? (
                <div className="flex items-center gap-2">
                  <Input
                    defaultValue={clusterData.docType}
                    className="w-48"
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        handleDocTypeChange(clusterId, e.target.value);
                      }
                    }}
                  />
                  <Button 
                    size="sm"
                    onClick={() => toggleDocTypeEdit(clusterId)}
                  >
                    <Check className="w-4 h-4" />
                  </Button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <span className="font-medium">Cluster {clusterId}: {clusterData.docType}</span>
                  <button
                    onClick={() => toggleDocTypeEdit(clusterId)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>

            <div className="flex items-center gap-2">
              <Badge 
                variant={clusterData.isIndependent ? "success" : "secondary"}
                className="cursor-pointer"
                onClick={() => toggleIndependentStatus(clusterId)}
              >
                {clusterData.isIndependent ? "Unabhängig" : "Prozessabhängig"}
              </Badge>
              <span className="text-sm text-gray-500">
                {clusterData.files.length} Dateien
              </span>
            </div>
          </div>

          {expandedClusters[clusterId] && (
            <div className="ml-12 space-y-2">
              {clusterData.files.map((file, index) => (
                <div 
                  key={index}
                  className="flex items-center gap-2 p-2 hover:bg-gray-50 rounded"
                >
                  <input
                    type="checkbox"
                    checked={selectedFiles.includes(`${clusterId}-${file.filename}`)}
                    onChange={() => toggleFileSelection(clusterId, file.filename)}
                    className="rounded"
                  />
                  <span className="text-sm">{file.filename}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      ))}
    </div>
  );
};

export default ClusterManagement;