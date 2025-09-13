import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import './MapView.css';
import './Dropdown.css';
import axios from 'axios';
import { API_BASE_URL, MAPBOX_TOKEN } from '../config';
import Chatbot from './Chatbot';

// Set your Mapbox token
mapboxgl.accessToken = MAPBOX_TOKEN;

function MapView() {
  const mapContainer = useRef(null);
  const map = useRef(null);
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [neighborhoods, setNeighborhoods] = useState([]);
  const [selectedNeighborhood, setSelectedNeighborhood] = useState(null);
  const [stats, setStats] = useState(null);
  const [selectedLayer, setSelectedLayer] = useState('green_score');
  const [expandedItems, setExpandedItems] = useState(new Set());
  const [showChatbot, setShowChatbot] = useState(false);
  
  // New state for layer toggles
  const [showNeighborhoods, setShowNeighborhoods] = useState(true);
  const [showLEWC, setShowLEWC] = useState(false);
const [selectedDisasters, setSelectedDisasters] = useState(new Set());
const [availableDisasters, setAvailableDisasters] = useState([]);
  const [lewcData, setLEWCData] = useState(null);
  const [lewcMarkers, setLEWCMarkers] = useState([]);

  const interpolateColor = (score, startColor, endColor) => {
    if (score === null || score === undefined) return '#808080';
    const ratio = score / 10;
    const r = Math.ceil(parseInt(startColor.substring(1, 3), 16) * ratio + parseInt(endColor.substring(1, 3), 16) * (1 - ratio));
    const g = Math.ceil(parseInt(startColor.substring(3, 5), 16) * ratio + parseInt(endColor.substring(3, 5), 16) * (1 - ratio));
    const b = Math.ceil(parseInt(startColor.substring(5, 7), 16) * ratio + parseInt(endColor.substring(5, 7), 16) * (1 - ratio));
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
  };

  const getScoreColor = (score, layer) => {
    if (score === null || score === undefined) return '#808080';

    switch (layer) {
        case 'green_score':
            if (score >= 8.5) return '#2ecc71';
            if (score >= 8.0) return '#f1c40f';
            if (score >= 7.5) return '#e67e22';
            return '#e74c3c';
        case 'air_quality':
        case 'greenery_coverage':
        case 'water_quality':
        case 'cleanliness':
        case 'road_quality':
        case 'public_safety':
        case 'walkability':
        case 'public_transit_access':
        case 'renewable_energy_adoption':
        case 'recycling_rate':
        case 'local_business_sustainability_practices':
        case 'circular_economy_indicators':
            return interpolateColor(score, '#2ecc71', '#e74c3c');
        case 'power_grid_reliability':
            return interpolateColor(score, '#f1c40f', '#a52a2a');
        default:
            return '#808080';
    }
  };

// Load LEWC data
const loadLEWCData = async () => {
  try {
    // Use the API endpoint instead of direct file access
    const response = await axios.get(`${API_BASE_URL}/api/lewc`);
    if (response.data.success) {
      const data = response.data.data;
      setLEWCData(data);
      
      // Extract available disasters from the loaded data
      const disasters = Object.keys(data).map(disasterType => ({
        id: disasterType.toLowerCase().replace(/\s+/g, '_').replace(/[()]/g, ''),
        name: disasterType,
        description: data[disasterType].description,
        color: data[disasterType].map_color,
        hasHotspots: data[disasterType].hotspots && data[disasterType].hotspots.length > 0
      }));
      setAvailableDisasters(disasters);
      
      console.log('LEWC data loaded:', data);
      console.log('Available disasters:', disasters);
    } else {
      throw new Error('Failed to load LEWC data from API');
    }
  } catch (error) {
    console.warn('Could not load LEWC data:', error);
    // Fallback disasters list
    setAvailableDisasters([
      { id: 'extreme_heat', name: 'Extreme Heat', description: 'Dangerously high temperatures', color: '#FF4500', hasHotspots: true },
      { id: 'flash_floods', name: 'Flash Floods', description: 'Rapid flooding of low-lying areas', color: '#0000FF', hasHotspots: true },
      { id: 'wildfire', name: 'Wildfire', description: 'Risk of fires in brush areas', color: '#FF0000', hasHotspots: true },
      { id: 'drought', name: 'Drought', description: 'Prolonged period of low rainfall', color: '#FFA500', hasHotspots: true },
      { id: 'dust_storms_haboob', name: 'Dust Storms (Haboob)', description: 'Intense dust storms reducing visibility', color: '#8B4513', hasHotspots: true },
      { id: 'severe_thunderstorm', name: 'Severe Thunderstorm', description: 'Storms with strong winds and lightning', color: '#4B0082', hasHotspots: true },
      { id: 'earthquake', name: 'Earthquake', description: 'Minor seismic activity possible', color: '#A0522D', hasHotspots: false },
      { id: 'tornado', name: 'Tornado', description: 'Rare but possible tornadoes', color: '#808080', hasHotspots: false },
      { id: 'cyclone_remnant', name: 'Cyclone (Remnant)', description: 'Remnants of Pacific hurricanes', color: '#2E8B57', hasHotspots: false }
    ]);
  }
};

  // Toggle expanded state for score items
  const toggleExpanded = (key) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(key)) {
      newExpanded.delete(key);
    } else {
      newExpanded.add(key);
    }
    setExpandedItems(newExpanded);
  };

// Add LEWC overlays to map
const addLEWCOverlays = () => {
  if (!map.current || !lewcData || selectedDisasters.size === 0) return;

  // Remove existing LEWC markers
  lewcMarkers.forEach(marker => marker.remove());
  setLEWCMarkers([]);

  const newMarkers = [];

  // Only show selected disasters
  Object.entries(lewcData).forEach(([disasterType, data]) => {
    const disasterId = disasterType.toLowerCase().replace(/\s+/g, '_');
    
    // Check if this disaster type is selected
    if (!selectedDisasters.has(disasterId)) return;
    
    // Skip disasters without hotspots
    if (!data.hotspots || data.hotspots.length === 0) return;

    data.hotspots.forEach((hotspot, index) => {
      // Create circle overlay
      const canvas = document.createElement('canvas');
      const size = Math.max(40, Math.min(100, hotspot.radius_meters / 50));
      canvas.width = size;
      canvas.height = size;
      const ctx = canvas.getContext('2d');

      // Draw circle
      ctx.beginPath();
      ctx.arc(size / 2, size / 2, size / 2 - 2, 0, 2 * Math.PI);
      ctx.fillStyle = data.map_color + '40'; // Add transparency
      ctx.fill();
      ctx.strokeStyle = data.map_color;
      ctx.lineWidth = 2;
      ctx.stroke();

      // Create marker element
      const el = document.createElement('div');
      el.appendChild(canvas);
      el.style.cursor = 'pointer';
      el.className = 'lewc-marker';

      // Create popup content
      const popupContent = `
        <div class="lewc-popup">
          <h3 style="margin: 0 0 8px 0; color: ${data.map_color};">${disasterType}</h3>
          <p style="margin: 0; font-size: 0.9rem; line-height: 1.4;">${data.description}</p>
          <div style="margin-top: 8px; font-size: 0.8rem; opacity: 0.8;">
            Risk radius: ~${(hotspot.radius_meters / 1000).toFixed(1)} km
          </div>
        </div>
      `;

      // Create marker
      const marker = new mapboxgl.Marker(el)
        .setLngLat([hotspot.lng, hotspot.lat])
        .setPopup(new mapboxgl.Popup({ 
          offset: 25,
          className: 'lewc-popup-container'
        }).setHTML(popupContent))
        .addTo(map.current);

      newMarkers.push(marker);
    });
  });

  setLEWCMarkers(newMarkers);
};
  // Remove LEWC overlays
  const removeLEWCOverlays = () => {
    lewcMarkers.forEach(marker => marker.remove());
    setLEWCMarkers([]);
  };

  // Toggle neighborhood markers
  const toggleNeighborhoodMarkers = (show) => {
    const markers = document.querySelectorAll('.custom-marker');
    markers.forEach(marker => {
      marker.style.display = show ? 'block' : 'none';
    });
  };

  // Handle layer toggle changes
useEffect(() => {
  if (showLEWC && selectedDisasters.size > 0) {
    addLEWCOverlays();
  } else {
    removeLEWCOverlays();
  }
}, [showLEWC, selectedDisasters, lewcData]);

  useEffect(() => {
    toggleNeighborhoodMarkers(showNeighborhoods);
  }, [showNeighborhoods]);

  // Reset expanded items when neighborhood changes
  useEffect(() => {
    setExpandedItems(new Set());
  }, [selectedNeighborhood]);

  useEffect(() => {
    if (map.current) return; // Initialize map only once

    try {
      map.current = new mapboxgl.Map({
        container: mapContainer.current,
        style: 'mapbox://styles/mapbox/dark-v11',
        center: [-111.9400, 33.4255], // Tempe, AZ coordinates
        zoom: 11,
        pitch: 45,
        bearing: -17.6,
        antialias: true
      });

      map.current.on('load', async () => {
        setLoading(false);
        map.current.addControl(new mapboxgl.NavigationControl(), 'top-right');

        // Load LEWC data
        await loadLEWCData();

        try {
          // Fetch neighborhood data
          const response = await axios.get(`${API_BASE_URL}/api/neighborhoods`);
          if (response.data.success) {
            const neighborhoodsData = response.data.data.filter(n => n.coordinates && n.coordinates.lng && n.coordinates.lat);
            setNeighborhoods(neighborhoodsData);

            // Fetch summary stats
            const statsResponse = await axios.get(`${API_BASE_URL}/api/neighborhoods/stats/summary`);
            if (statsResponse.data.success) {
                setStats(statsResponse.data.data);
            }

            // Add markers for each neighborhood
            neighborhoodsData.forEach(neighborhood => {
                if (neighborhood.coordinates) {
                    const score = selectedLayer === 'green_score' ? neighborhood.green_score : neighborhood.score_variables[selectedLayer];
                    const el = document.createElement('div');
                    el.className = 'custom-marker';
                    el.style.backgroundColor = getScoreColor(score, selectedLayer);
                    el.style.width = '20px';
                    el.style.height = '20px';
                    el.style.borderRadius = '50%';
                    el.style.border = '2px solid #ffffff';

                    const marker = new mapboxgl.Marker(el)
                        .setLngLat([neighborhood.coordinates.lng, neighborhood.coordinates.lat])
                        .setPopup(new mapboxgl.Popup({ offset: 25 }).setHTML(`
                            <div class="popup-content">
                                <h3>${neighborhood.name}</h3>
                                <p>${selectedLayer.replace(/_/g, ' ')}: <span class="popup-score">${score ? score.toFixed(2) : 'N/A'}</span></p>
                            </div>
                        `))
                        .addTo(map.current);
                    
                    marker.getElement().addEventListener('click', () => {
                        setSelectedNeighborhood(neighborhood);
                        map.current.flyTo({
                            center: [neighborhood.coordinates.lng, neighborhood.coordinates.lat],
                            zoom: 14,
                            pitch: 60
                        });
                    });
                }
            });
          } else {
            setError('Failed to fetch neighborhood data.');
          }
        } catch (apiError) {
          console.error('API Error:', apiError);
          setError('Could not connect to the backend API.');
        }
      });

      map.current.on('error', (e) => {
        console.error('Mapbox GL Error:', e);
        setError('Map failed to load. Check your Mapbox token.');
        setLoading(false);
      });

    } catch (err) {
      console.error('Map Initialization Error:', err);
      setError('An unexpected error occurred while initializing the map.');
      setLoading(false);
    }

    return () => {
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!map.current || !neighborhoods.length) return;

    // Remove existing markers
    document.querySelectorAll('.mapboxgl-marker').forEach(marker => {
      if (marker.querySelector('.custom-marker')) {
        marker.remove();
      }
    });

    neighborhoods.forEach(neighborhood => {
        if (neighborhood.coordinates) {
            const score = selectedLayer === 'green_score' ? neighborhood.green_score : neighborhood.score_variables[selectedLayer];
            const el = document.createElement('div');
            el.className = 'custom-marker';
            el.style.backgroundColor = getScoreColor(score, selectedLayer);
            el.style.width = '20px';
            el.style.height = '20px';
            el.style.borderRadius = '50%';
            el.style.border = '2px solid #ffffff';

            const marker = new mapboxgl.Marker(el)
                .setLngLat([neighborhood.coordinates.lng, neighborhood.coordinates.lat])
                .setPopup(new mapboxgl.Popup({ offset: 25 }).setHTML(`
                    <div class="popup-content">
                        <h3>${neighborhood.name}</h3>
                        <p>${selectedLayer.replace(/_/g, ' ')}: <span class="popup-score">${score ? score.toFixed(2) : 'N/A'}</span></p>
                    </div>
                `))
                .addTo(map.current);
            
            marker.getElement().addEventListener('click', () => {
                setSelectedNeighborhood(neighborhood);
                map.current.flyTo({
                    center: [neighborhood.coordinates.lng, neighborhood.coordinates.lat],
                    zoom: 14,
                    pitch: 60
                });
            });
        }
    });

    // Re-apply neighborhood visibility
    toggleNeighborhoodMarkers(showNeighborhoods);

  }, [selectedLayer, neighborhoods, showNeighborhoods]);

  // Helper function to format variable names for display
  const formatVariableName = (key) => {
    return key.replace(/_/g, ' ')
             .replace(/\b\w/g, l => l.toUpperCase());
  };

  // Helper function to get variable explanation
  const getVariableExplanation = (key) => {
    if (!selectedNeighborhood) return '';
    const expKey = key + '_exp';
    const reasonKey = key + '_reason';
    return selectedNeighborhood.score_variables[expKey] || 
           selectedNeighborhood.score_variables[reasonKey] || 
           'No detailed explanation available for this metric.';
  };

  const layerOptions = [
      { value: 'green_score', label: 'Green Score' },
      { value: 'air_quality', label: 'Air Quality' },
      { value: 'greenery_coverage', label: 'Greenery Coverage' },
      { value: 'water_quality', label: 'Water Quality' },
      { value: 'cleanliness', label: 'Cleanliness' },
      { value: 'power_grid_reliability', label: 'Power Grid Reliability' },
      { value: 'road_quality', label: 'Road Quality' },
      { value: 'public_safety', label: 'Public Safety' },
      { value: 'walkability', label: 'Walkability' },
      { value: 'public_transit_access', label: 'Public Transit Access' },
      { value: 'renewable_energy_adoption', label: 'Renewable Energy Adoption' },
      { value: 'recycling_rate', label: 'Recycling Rate' },
      { value: 'local_business_sustainability_practices', label: 'Business Sustainability' },
      { value: 'circular_economy_indicators', label: 'Circular Economy' },
  ];

  return (
    <div className="map-container">
        <div className="map-header">
            <button className="back-button" onClick={() => navigate('/')}>
            ← Back to Home
            </button>
            <h1 className="map-title">Urban Vitals - Tempe</h1>
            <div className="dropdown-container">
                <select className="dropdown" value={selectedLayer} onChange={e => setSelectedLayer(e.target.value)}>
                    {layerOptions.map(option => (
                        <option key={option.value} value={option.value}>{option.label}</option>
                    ))}
                </select>
            </div>
            {stats && (
            <div className="stats-bar">
                <span>Total: <strong>{stats.total_neighborhoods}</strong></span>
                <span>Avg. Score: <strong>{stats.average_green_score.toFixed(2)}</strong></span>
                <span>Highest: <strong>{stats.highest_green_score.toFixed(2)}</strong></span>
                <span>Lowest: <strong>{stats.lowest_green_score.toFixed(2)}</strong></span>
            </div>
            )}
        </div>

      {loading && (
        <div className="loading-overlay">
          <div className="loader"></div>
          <p>Loading map...</p>
        </div>
      )}

      {error && (
        <div className="error-overlay">
          <h2>Error Loading Map</h2>
          <p>{error}</p>
        </div>
      )}

        <div ref={mapContainer} className="map-viewport" />
        
        {/* Layer Controls */}
<div className="layer-controls">
  <h4>Map Layers</h4>
  <div className="layer-toggle">
    <label className="toggle-label">
      <input 
        type="checkbox" 
        checked={showNeighborhoods}
        onChange={(e) => setShowNeighborhoods(e.target.checked)}
      />
      <span className="toggle-slider"></span>
      Neighborhoods
    </label>
  </div>
  <div className="layer-toggle">
    <label className="toggle-label">
      <input 
        type="checkbox" 
        checked={showLEWC}
        onChange={(e) => {
          setShowLEWC(e.target.checked);
          if (!e.target.checked) {
            setSelectedDisasters(new Set());
          }
        }}
      />
      <span className="toggle-slider"></span>
      LEWC (Disaster Risk)
    </label>
  </div>
  {/* Disaster Selection Panel */}
  {showLEWC && (
    <div className="disaster-selection-panel">
      <h5>Select Disasters:</h5>
      <div className="disaster-checkboxes">
        {availableDisasters.map((disaster) => (
          <div key={disaster.id} className="disaster-checkbox-item">
            <label className="disaster-checkbox-label">
              <input
                type="checkbox"
                checked={selectedDisasters.has(disaster.id)}
                onChange={(e) => {
                  const newSelected = new Set(selectedDisasters);
                  if (e.target.checked) {
                    newSelected.add(disaster.id);
                  } else {
                    newSelected.delete(disaster.id);
                  }
                  setSelectedDisasters(newSelected);
                }}
                disabled={!disaster.hasHotspots}
              />
              <span 
                className="disaster-color-dot" 
                style={{ backgroundColor: disaster.color }}
              ></span>
              <span className={!disaster.hasHotspots ? 'disabled-disaster' : ''}>
                {disaster.name}
              </span>
            </label>
            {!disaster.hasHotspots && (
              <span className="no-hotspots-indicator" title="No location data available">
                ⚠️
              </span>
            )}
          </div>
        ))}
      </div>
      <div className="disaster-selection-actions">
        <button 
          className="select-all-btn"
          onClick={() => {
            const activeDisasters = availableDisasters
              .filter(d => d.hasHotspots)
              .map(d => d.id);
            setSelectedDisasters(new Set(activeDisasters));
          }}
        >
          Select All
        </button>
        <button 
          className="clear-all-btn"
          onClick={() => setSelectedDisasters(new Set())}
        >
          Clear All
        </button>
      </div>
    </div>
  )}
</div>
        
        {/* Chatbot Button */}
        <button 
          className="chatbot-toggle-button"
          onClick={() => setShowChatbot(true)}
          title="Ask Urban Vitals Assistant"
        >
          🤖
        </button>
        
        {selectedNeighborhood && (
            <div className="detail-panel">
                <button className="close-button" onClick={() => setSelectedNeighborhood(null)}>&times;</button>
                <h2>{selectedNeighborhood.name}</h2>
                
                {/* Ask AI Button */}
                <button 
                  className="ask-ai-button"
                  onClick={() => setShowChatbot(true)}
                >
                  🤖 Ask AI about this neighborhood
                </button>
                
                <div className="score-display" style={{ 
                    background: `linear-gradient(135deg, ${getScoreColor(selectedLayer === 'green_score' ? selectedNeighborhood.green_score : selectedNeighborhood.score_variables[selectedLayer], selectedLayer)}, ${getScoreColor(selectedLayer === 'green_score' ? selectedNeighborhood.green_score : selectedNeighborhood.score_variables[selectedLayer], selectedLayer)}cc)` 
                }}>
                    <div className="score-value">
                        {selectedLayer === 'green_score' 
                            ? selectedNeighborhood.green_score?.toFixed(2) 
                            : selectedNeighborhood.score_variables[selectedLayer]?.toFixed(2) || 'N/A'}
                    </div>
                    <div className="score-label">{formatVariableName(selectedLayer)}</div>
                </div>
                <p className="description">{selectedNeighborhood.description}</p>
                
                {/* Show explanation for selected layer */}
                {selectedLayer !== 'green_score' && getVariableExplanation(selectedLayer) && (
                    <div className="explanation">
                        <h4>About {formatVariableName(selectedLayer)}:</h4>
                        <p>{getVariableExplanation(selectedLayer)}</p>
                    </div>
                )}
                
                <div className="score-breakdown">
                    <h3>Score Breakdown</h3>
                    <div className="variables">
                        {Object.entries(selectedNeighborhood.score_variables)
                            .filter(([key, value]) => 
                                !key.endsWith('_exp') && 
                                !key.endsWith('_reason') && 
                                !key.endsWith('_explanation') &&
                                typeof value === 'number'
                            )
                            .map(([key, value]) => {
                                const isExpanded = expandedItems.has(key);
                                const explanation = getVariableExplanation(key);
                                
                                return (
                                    <div key={key} className="variable-container">
                                        <div 
                                            className="variable clickable" 
                                            onClick={() => toggleExpanded(key)}
                                        >
                                            <span>{formatVariableName(key)}</span>
                                            <div className="variable-right">
                                                <span className="value">{value}/10</span>
                                                <span className={`expand-arrow ${isExpanded ? 'expanded' : ''}`}>
                                                    ▼
                                                </span>
                                            </div>
                                        </div>
                                        {isExpanded && explanation && (
                                            <div className="variable-explanation">
                                                {explanation}
                                            </div>
                                        )}
                                    </div>
                                );
                            })
                        }
                    </div>
                </div>
            </div>
        )}

        <div className="legend">
            <h4>{formatVariableName(selectedLayer)}</h4>
            <div className="legend-items">
                {[10, 8, 6, 4, 2].map((score) => (
                    <div className="legend-item" key={score}>
                        <div className="legend-dot" style={{ backgroundColor: getScoreColor(score, selectedLayer) }}></div>
                        <span>{score}</span>
                    </div>
                ))}
            </div>
        </div>

        {/* Chatbot Component */}
        <Chatbot 
          selectedNeighborhood={selectedNeighborhood}
          onClose={() => setShowChatbot(false)}
          isVisible={showChatbot}
        />
    </div>
  );
}

export default MapView;