import React from 'react';

const ObjectTypeDisplay = () => {
  const [objectTypes, setObjectTypes] = React.useState([]);
  const [expandedTypes, setExpandedTypes] = React.useState({});
  const [independentTypes, setIndependentTypes] = React.useState([]);
  const [isProcessing, setIsProcessing] = React.useState(false);

  React.useEffect(() => {
    // Initialize independent types from current data
    const initialIndependentTypes = objectTypes
      .filter(type => type.category === 'INDEPENDENT')
      .map(type => type.name);
    setIndependentTypes(initialIndependentTypes);
  }, [objectTypes]);

  const reclassify = async () => {
    try {
      setIsProcessing(true);
      // Send updated independent types to Python
      if (window.qt && window.qt.webChannelTransport) {
        new QWebChannel(qt.webChannelTransport, function(channel) {
          channel.objects.pybridge.updateProcessInstanceIndependence(
            independentTypes,
            objectTypes
          );
        });
      }
    } catch (error) {
      console.error('Reclassification error:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleToggleIndependent = (typeName) => {
    setIndependentTypes(prev => 
      prev.includes(typeName) 
        ? prev.filter(name => name !== typeName)
        : [...prev, typeName]
    );
  };

  return (
    <div className="max-w-4xl mx-auto p-4">
      {objectTypes.map(type => (
        <div key={type.id} className="bg-white rounded-lg shadow mb-4 border border-gray-200">
          <div className="p-4 flex justify-between items-center cursor-pointer"
               onClick={() => setExpandedTypes(prev => ({ ...prev, [type.id]: !prev[type.id] }))}>
            <div className="flex items-center gap-2">
              <span className="font-semibold">{type.name}</span>
              <span className={`px-2 py-1 rounded-full text-sm ${
                type.category === 'PROCESS_INSTANCE' ? 'bg-green-100 text-green-800' :
                type.category === 'INDEPENDENT' ? 'bg-blue-100 text-blue-800' :
                'bg-yellow-100 text-yellow-800'
              }`}>
                {type.category}
              </span>
            </div>
            <span>{expandedTypes[type.id] ? '▼' : '▶'}</span>
          </div>
          
          {expandedTypes[type.id] && (
            <div className="p-4 border-t border-gray-200">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-gray-50 p-4 rounded-lg">
                <div>
                  <span className="text-gray-500 text-sm">Files</span>
                  <div className="font-semibold">{type.fileCount}</div>
                </div>
                <div>
                  <span className="text-gray-500 text-sm">Instances</span>
                  <div className="font-semibold">{type.instances}</div>
                </div>
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id={`independent-${type.id}`}
                    checked={independentTypes.includes(type.name)}
                    onChange={() => handleToggleIndependent(type.name)}
                    disabled={isProcessing}
                    className="mr-2"
                  />
                  <label htmlFor={`independent-${type.id}`} className="text-sm">
                    Process Instance Independent
                  </label>
                </div>
              </div>
            </div>
          )}
        </div>
      ))}
      
      <button 
        onClick={reclassify}
        disabled={isProcessing}
        className="w-full mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
      >
        {isProcessing ? 'Reclassifying...' : 'Reclassify All'}
      </button>
    </div>
  );
};

export default ObjectTypeDisplay;