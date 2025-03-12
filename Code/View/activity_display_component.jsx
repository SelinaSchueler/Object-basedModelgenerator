import React from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ArrowRight, Clock, FileText, ArrowRightLeft, ChevronDown, ChevronUp } from 'lucide-react';

const ActivityDisplay = () => {
  const [expandedActivities, setExpandedActivities] = React.useState({});

  const toggleExpand = (activityId) => {
    setExpandedActivities(prev => ({
      ...prev,
      [activityId]: !prev[activityId]
    }));
  };

  const ActivityCard = ({ activity, type }) => {
    const isExpanded = expandedActivities[activity.id];
    
    return (
      <Card className="mb-4 border-l-4 hover:shadow-md transition-shadow" 
            style={{ borderLeftColor: type === 'content' ? '#3b82f6' : '#10b981' }}>
        <CardHeader className="flex flex-row items-center justify-between p-4 cursor-pointer"
                   onClick={() => toggleExpand(activity.id)}>
          <div className="flex items-center space-x-2">
            {type === 'content' ? 
              <FileText className="w-5 h-5 text-blue-500" /> : 
              <Clock className="w-5 h-5 text-emerald-500" />
            }
            <h3 className="text-lg font-semibold">{activity.name}</h3>
          </div>
          {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </CardHeader>
        
        {isExpanded && (
          <CardContent className="p-4 pt-0">
            <div className="grid gap-4">
              {/* Flow Display */}
              <div className="flex items-center justify-center space-x-4 py-2">
                <div className="flex flex-col items-center">
                  {activity.inputTypes.map((input, idx) => (
                    <Badge key={idx} className="m-1 bg-gray-100 text-gray-700">
                      {input}
                    </Badge>
                  ))}
                </div>
                <ArrowRight className="w-6 h-6 text-gray-400" />
                <div className="flex flex-col items-center">
                  {activity.outputTypes.map((output, idx) => (
                    <Badge key={idx} className="m-1 bg-gray-100 text-gray-700">
                      {output}
                    </Badge>
                  ))}
                </div>
              </div>

              {/* Rules Section */}
              {activity.rules && activity.rules.length > 0 && (
                <div className="mt-4">
                  <h4 className="font-semibold mb-2">Rules:</h4>
                  <div className="space-y-2">
                    {activity.rules.map((rule, idx) => (
                      <div key={idx} className="flex items-center p-2 bg-gray-50 rounded">
                        <ArrowRightLeft className="w-4 h-4 mr-2 text-gray-500" />
                        <span>{rule}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Instances Counter */}
              {activity.instanceCount && (
                <div className="text-sm text-gray-500 mt-2">
                  Process Instances: {activity.instanceCount}
                </div>
              )}
            </div>
          </CardContent>
        )}
      </Card>
    );
  };

  return (
    <div className="max-w-4xl mx-auto p-4 space-y-6">
      <div className="grid gap-6">
        <section>
          <h2 className="text-xl font-bold mb-4 flex items-center">
            <FileText className="w-5 h-5 mr-2 text-blue-500" />
            Content-based Activities
          </h2>
          <div className="space-y-4">
            <ActivityCard 
              activity={{
                id: 'c1',
                name: 'Order Processing',
                inputTypes: ['Order', 'Customer'],
                outputTypes: ['Invoice'],
                rules: ['Match customer ID', 'Calculate total amount'],
                instanceCount: 150
              }}
              type="content"
            />
            <ActivityCard 
              activity={{
                id: 'c2',
                name: 'Payment Verification',
                inputTypes: ['Payment', 'Invoice'],
                outputTypes: ['Receipt'],
                rules: ['Verify payment amount', 'Match invoice number'],
                instanceCount: 120
              }}
              type="content"
            />
          </div>
        </section>

        <section>
          <h2 className="text-xl font-bold mb-4 flex items-center">
            <Clock className="w-5 h-5 mr-2 text-emerald-500" />
            Time-based Activities
          </h2>
          <div className="space-y-4">
            <ActivityCard 
              activity={{
                id: 't1',
                name: 'Shipping Process',
                inputTypes: ['Order'],
                outputTypes: ['Shipment'],
                instanceCount: 85
              }}
              type="time"
            />
            <ActivityCard 
              activity={{
                id: 't2',
                name: 'Delivery Confirmation',
                inputTypes: ['Shipment'],
                outputTypes: ['Delivery'],
                instanceCount: 72
              }}
              type="time"
            />
          </div>
        </section>
      </div>
    </div>
  );
};

export default ActivityDisplay;