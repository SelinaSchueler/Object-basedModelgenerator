import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { 
  Settings2, Scale, Timer, GitBranch, 
  ArrowDownUp, Shield, Info,
  ChevronDown, ChevronRight 
} from "lucide-react";

const SettingsView = () => {
  const [settings, setSettings] = useState({
    same_value_threshold: 80,
    significant_instance_threshold: 90,
    rule_significance_threshold: 90,
    temporal_weight: 400,
    reference_weight: 200,
    sequence_weight: 150,
    attribute_weight: 120,
    early_position_bonus: 150,
    late_position_penalty: 50,
    reference_position_factor: 200,
    parallel_object_penalty: 600,
    each_attribute_by_object: false,
    database_visualization: false
  });

  const [expandedSections, setExpandedSections] = useState({});
  const [expandedHelp, setExpandedHelp] = useState({});

  const toggleSection = (section) => {
    setExpandedSections(prev => ({...prev, [section]: !prev[section]}));
  };

  const toggleHelp = (key) => {
    setExpandedHelp(prev => ({...prev, [key]: !prev[key]}));
  };

  const handleSettingChange = (key, value) => {
    setSettings(prev => ({
      ...prev,
      [key]: typeof value === 'object' ? value[0] : value
    }));
  };

  const settingSections = {
    thresholds: {
      title: "Threshold Settings",
      description: "Core analysis parameters for pattern recognition",
      icon: Scale,
      settings: [
        {
          key: 'same_value_threshold',
          label: 'Similar Value Match',
          description: 'Minimum similarity required between values',
          help: 'Controls how strictly values must match to be considered equivalent',
          max: 100,
          defaultValue: 80
        },
        {
          key: 'significant_instance_threshold',
          label: 'Instance Significance',
          description: 'Required percentage for pattern significance',
          help: 'Determines how many instances must exhibit a pattern for it to be considered significant',
          max: 100,
          defaultValue: 90
        },
        {
          key: 'rule_significance_threshold',
          label: 'Rule Significance',
          description: 'Confidence threshold for rules',
          help: 'Minimum confidence level required for rule extraction',
          max: 100,
          defaultValue: 90
        }
      ]
    },
    weights: {
      title: "Weight Settings",
      description: "Impact factors for different analysis aspects",
      icon: Timer,
      settings: [
        {
          key: 'temporal_weight',
          label: 'Time Weighting',
          description: 'Impact of temporal relationships',
          help: 'Weight given to time-based relationships between documents',
          max: 500,
          defaultValue: 400
        },
        {
          key: 'reference_weight',
          label: 'Reference Weight',
          description: 'Importance of cross-references',
          help: 'Weight given to explicit references between documents',
          max: 300,
          defaultValue: 200
        },
        {
          key: 'sequence_weight',
          label: 'Sequence Weight',
          description: 'Impact of process patterns',
          help: 'Importance given to sequential patterns in the process',
          max: 200,
          defaultValue: 150
        },
        {
          key: 'attribute_weight',
          label: 'Attribute Weight',
          description: 'Importance of attributes',
          help: 'Weight given to attribute-based relationships',
          max: 200,
          defaultValue: 120
        }
      ]
    },
    positions: {
      title: "Position & Penalty Settings",
      description: "Parameters affecting document positioning and timing",
      icon: ArrowDownUp,
      settings: [
        {
          key: 'early_position_bonus',
          label: 'Early Position',
          description: 'Bonus for early documents',
          help: 'Additional weight given to documents appearing early in the process',
          max: 200,
          defaultValue: 150
        },
        {
          key: 'late_position_penalty',
          label: 'Late Position',
          description: 'Penalty for late documents',
          help: 'Reduction factor applied to documents appearing late in the process',
          max: 100,
          defaultValue: 50
        },
        {
          key: 'reference_position_factor',
          label: 'Position Factor',
          description: 'Impact of positions',
          help: 'Influence of document position on reference relationships',
          max: 300,
          defaultValue: 200
        },
        {
          key: 'parallel_object_penalty',
          label: 'Parallel Penalty',
          description: 'Penalty for concurrent processing',
          help: 'Reduction factor applied to concurrent document processing',
          max: 1000,
          defaultValue: 600
        }
      ]
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <Card className="border-t-4 border-t-blue-500">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Settings2 className="w-6 h-6 text-blue-500" />
            <CardTitle>Advanced Process Analysis Settings</CardTitle>
          </div>
          <CardDescription className="text-base">
            Configure detailed parameters to optimize process mining results
          </CardDescription>
        </CardHeader>
      </Card>

      {Object.entries(settingSections).map(([section, { title, description, icon: Icon, settings }]) => (
        <Card key={section} className="border-l-4 border-l-gray-200 hover:border-l-blue-500 transition-colors">
          <CardHeader className="cursor-pointer" onClick={() => toggleSection(section)}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Icon className="w-5 h-5 text-blue-500" />
                <div>
                  <CardTitle className="text-lg">{title}</CardTitle>
                  <CardDescription>{description}</CardDescription>
                </div>
              </div>
              {expandedSections[section] ? 
                <ChevronDown className="w-5 h-5" /> : 
                <ChevronRight className="w-5 h-5" />
              }
            </div>
          </CardHeader>

          {expandedSections[section] && (
            <CardContent className="space-y-6 pt-2">
              {settings.map(({ key, label, description, help, max, defaultValue }) => (
                <div key={key} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">{label}</span>
                        <Info 
                          className="w-4 h-4 text-gray-400 cursor-pointer hover:text-blue-500"
                          onClick={() => toggleHelp(key)}
                        />
                      </div>
                      <p className="text-sm text-gray-500">{description}</p>
                    </div>
                    <span className="text-sm font-medium">
                      {max === 100 ? `${settings[key]}%` : (settings[key]/100).toFixed(1)}
                    </span>
                  </div>

                  {expandedHelp[key] && (
                    <Alert className="bg-blue-50 border-blue-200">
                      <AlertDescription className="text-sm">{help}</AlertDescription>
                    </Alert>
                  )}

                  <Slider 
                    value={[settings[key]]}
                    max={max}
                    step={max === 100 ? 1 : 10}
                    onValueChange={(value) => handleSettingChange(key, value)}
                    className="pt-2"
                  />
                </div>
              ))}
            </CardContent>
          )}
        </Card>
      ))}

      <Card className="border-l-4 border-l-gray-200">
        <CardHeader>
          <CardTitle className="text-lg">Additional Options</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-sm font-medium">Individual Attribute Analysis</p>
              <p className="text-sm text-gray-500">Process and analyze each object attribute separately</p>
            </div>
            <Switch
              checked={settings.each_attribute_by_object}
              onCheckedChange={(checked) => handleSettingChange('each_attribute_by_object', checked)}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-sm font-medium">Database Visualization</p>
              <p className="text-sm text-gray-500">Enable advanced database relationship visualization</p>
            </div>
            <Switch
              checked={settings.database_visualization}
              onCheckedChange={(checked) => handleSettingChange('database_visualization', checked)}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default SettingsView;