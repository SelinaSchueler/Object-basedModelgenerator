import React, { useState } from 'react';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { ChevronDown, ChevronRight, Activity, GitBranch } from 'lucide-react';

const RuleExtractorDisplay = () => {
  const [expandedPoints, setExpandedPoints] = useState({});

  const toggleExpand = (pointId) => {
    setExpandedPoints(prev => ({
      ...prev,
      [pointId]: !prev[pointId]
    }));
  };

  // Example of how the rules data should be structured
  const [rules, setRules] = useState({});

  const DecisionPoint = ({ name, rules }) => {
    const isExpanded = expandedPoints[name];
    
    // Sort rules by importance
    const sortedRules = Object.entries(rules.importance || {})
      .sort(([,a], [,b]) => b - a);

    return (
      <Card className="mb-4 shadow-sm hover:shadow-md transition-shadow">
        <CardHeader 
          className="cursor-pointer flex flex-row items-center justify-between p-4"
          onClick={() => toggleExpand(name)}
        >
          <div className="flex items-center space-x-2">
            <GitBranch className="w-5 h-5 text-blue-500" />
            <h3 className="text-lg font-semibold">{name}</h3>
          </div>
          {isExpanded ? 
            <ChevronDown className="w-5 h-5" /> : 
            <ChevronRight className="w-5 h-5" />
          }
        </CardHeader>
        
        {isExpanded && (
          <CardContent className="p-4 pt-0">
            <div className="space-y-4">
              {/* Rules Section */}
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-2">Decision Rules</h4>
                <div className="space-y-2">
                  {sortedRules.map(([rule, importance], idx) => (
                    <div 
                      key={idx} 
                      className="flex items-center justify-between p-2 bg-gray-50 rounded-md"
                    >
                      <div className="flex items-center space-x-2">
                        <Activity className="w-4 h-4 text-gray-400" />
                        <span className="text-sm">{rule}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-blue-500 rounded-full"
                            style={{ width: `${importance * 100}%` }}
                          />
                        </div>
                        <span className="text-sm text-gray-500">
                          {(importance * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        )}
      </Card>
    );
  };

  return (
    <div className="max-w-4xl mx-auto p-4 space-y-4">
      <h2 className="text-2xl font-bold mb-6 flex items-center">
        <GitBranch className="w-6 h-6 mr-2 text-blue-500" />
        Decision Points Analysis
      </h2>
      
      {Object.entries(rules).map(([name, ruleInfo]) => (
        <DecisionPoint key={name} name={name} rules={ruleInfo} />
      ))}
      
      {Object.keys(rules).length === 0 && (
        <div className="text-center p-8 text-gray-500">
          No decision points analyzed yet
        </div>
      )}
    </div>
  );
};

export default RuleExtractorDisplay;