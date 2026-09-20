import { ops } from '../../pages/OperationsPage';
import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { LocationItem, HistoricalLandslide } from '../../types';
import { Layers, ShieldAlert, History as HistoryIcon, Eye, Radio } from 'lucide-react';

const escapeHtml=(value: unknown)=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]||c));

interface GISMapProps {
  locations: LocationItem[];
  historicalEvents?: HistoricalLandslide[];
  selectedLocation: LocationItem | null;
  onSelectLocation: (loc: LocationItem) => void;
}

export const GISMap: React.FC<GISMapProps> = ({
  locations,
  historicalEvents = [],
  selectedLocation,
  onSelectLocation,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const historicalLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const hazardZonesGroupRef = useRef<L.LayerGroup | null>(null);

  const [tileMode, setTileMode] = useState<'dark' | 'satellite' | 'topo'>('dark');
  const [showHazardZones, setShowHazardZones] = useState<boolean>(true);
  const [showHistorical, setShowHistorical] = useState<boolean>(true);

  const [showAssets,setShowAssets]=useState(true);
  const [assetError,setAssetError]=useState('');
  const [showRoads,setShowRoads]=useState(false),[roadError,setRoadError]=useState('');
  // Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    // Center on North East India (Brahmaputra Valley / Meghalaya / Nagaland hub)
    const map = L.map(mapContainerRef.current, {
      center: [25.8, 92.8],
      zoom: 7,
      minZoom: 5,
      maxZoom: 18,
      zoomControl: false,
    });

    L.control.zoom({ position: 'bottomright' }).addTo(map);

    markersLayerGroupRef.current = L.layerGroup().addTo(map);
    historicalLayerGroupRef.current = L.layerGroup().addTo(map);
    hazardZonesGroupRef.current = L.layerGroup().addTo(map);

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  useEffect(()=>{
    const map=mapInstanceRef.current;if(!map||!showAssets)return;
    const layer=L.layerGroup().addTo(map);let cancelled=false;
    ops('/priorities').then(items=>{if(cancelled)return;setAssetError('');items.forEach((a:any)=>{
      const node=document.createElement('div');node.textContent=`${a.name} (${a.kind}) · ${a.priority_score}/100 priority · ${a.population} exposed · ${a.access} access · Source: ${a.source}`;
      L.circleMarker([a.latitude,a.longitude],{radius:a.kind==='village'?11:8,color:a.priority==='URGENT'?'#fb7185':a.priority==='HIGH'?'#fbbf24':'#22d3ee',weight:3,fillOpacity:.6}).bindPopup(node).addTo(layer);
    });}).catch(()=>{if(!cancelled)setAssetError('Asset layer unavailable');});
    return()=>{cancelled=true;map.removeLayer(layer);};
  },[showAssets]);

  useEffect(()=>{
    const map=mapInstanceRef.current;if(!map||!showRoads)return;
    const layer=L.layerGroup().addTo(map);let cancelled=false;
    const load=()=>ops('/roads').then(items=>{if(cancelled)return;layer.clearLayers();setRoadError(items.length?'':'No surveyed links registered');items.forEach((r:any)=>{
      if(r.coordinates.length<2)return;
      const colors:any={open:'#34d399',restricted:'#fbbf24',blocked:'#fb7185',unknown:'#94a3b8'};
      const node=document.createElement('div');node.textContent=`${r.name} · ${r.effective_status.toUpperCase()} · ${r.schematic?'Schematic connection':'Surveyed road'} · Observed ${r.observed_at} · Source: ${r.source}${r.stale?' · STALE':''}`;
      L.polyline(r.coordinates.map((p:number[])=>[p[1],p[0]]),{color:colors[r.effective_status],weight:5,dashArray:r.schematic?'8 8':undefined}).bindPopup(node).addTo(layer);
    });}).catch(()=>{if(!cancelled)setRoadError('Road layer unavailable');});
    void load();const timer=setInterval(load,60000);
    return()=>{cancelled=true;clearInterval(timer);map.removeLayer(layer);};
  },[showRoads]);

  // Update Base Tile Layer
  useEffect(() => {
    if (!mapInstanceRef.current) return;
    const map = mapInstanceRef.current;

    // Remove existing tile layers
    map.eachLayer((layer) => {
      if (layer instanceof L.TileLayer) {
        map.removeLayer(layer);
      }
    });

    if (tileMode === 'dark') {
      L.tileLayer('https://services.arcgisonline.com/arcgis/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
        maxZoom: 16,
      }).addTo(map);
      L.tileLayer('https://services.arcgisonline.com/arcgis/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 16,
      }).addTo(map);
    } else if (tileMode === 'satellite') {
      L.tileLayer('https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS',
        maxZoom: 18,
      }).addTo(map);
      L.tileLayer('https://services.arcgisonline.com/arcgis/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 18,
      }).addTo(map);
    } else if (tileMode === 'topo') {
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(map);
    }
  }, [tileMode]);

  // Render Markers and Overlays
  useEffect(() => {
    if (!mapInstanceRef.current || !markersLayerGroupRef.current) return;
    const markersGroup = markersLayerGroupRef.current;
    const zonesGroup = hazardZonesGroupRef.current;
    const histGroup = historicalLayerGroupRef.current;

    markersGroup.clearLayers();
    if (zonesGroup) zonesGroup.clearLayers();
    if (histGroup) histGroup.clearLayers();

    // 1. Render Monitored Locations
    locations.forEach((loc) => {
      const score = loc.current_risk_score || 0;
      let color = '#10b981'; // Emerald
      let pulseClass = '';

      if (loc.risk_level === 'SEVERE') {
        color = '#ef4444'; // Red
        pulseClass = 'pulsing-severe';
      } else if (loc.risk_level === 'HIGH') {
        color = '#f97316'; // Orange
        pulseClass = 'pulsing-high';
      } else if (loc.risk_level === 'MODERATE') {
        color = '#f59e0b'; // Amber
      }

      const isSelected = selectedLocation?.location_id === loc.location_id;

      // Custom DivIcon marker
      const customIcon = L.divIcon({
        className: 'custom-landslide-marker',
        html: `
          <div style="
            display: flex;
            align-items: center;
            justify-content: center;
            width: ${isSelected ? 36 : 28}px;
            height: ${isSelected ? 36 : 28}px;
            border-radius: 50%;
            background: ${color};
            border: 2px solid #ffffff;
            box-shadow: 0 4px 12px rgba(0,0,0,0.6);
            color: #ffffff;
            font-weight: bold;
            font-family: monospace;
            font-size: ${isSelected ? 12 : 10}px;
            cursor: pointer;
            transition: transform 0.2s;
          " class="${pulseClass}">
            ${Math.round(score)}
          </div>
        `,
        iconSize: [isSelected ? 36 : 28, isSelected ? 36 : 28],
        iconAnchor: [isSelected ? 18 : 14, isSelected ? 18 : 14],
      });

      const marker = L.marker([loc.latitude, loc.longitude], { icon: customIcon });

      marker.bindPopup(`
        <div style="font-family: inherit; font-size: 12px; line-height: 1.4; min-width: 200px;">
          <div style="font-weight: bold; font-size: 13px; color: #f8fafc;">${escapeHtml(loc.name)}</div>
          <div style="color: #94a3b8; font-size: 11px; margin-bottom: 6px;">${escapeHtml(loc.district)}, ${escapeHtml(loc.state)}</div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
            <span>Risk Score:</span>
            <strong style="color: ${color};">${score.toFixed(1)} / 100 (${escapeHtml(loc.risk_level)})</strong>
          </div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
            <span>24h Rainfall:</span>
            <strong>${loc.latest_measurements?.rainfall_24h || 0} mm</strong>
          </div>
          <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
            <span>Slope / Elev:</span>
            <strong>${loc.slope}° / ${loc.elevation}m</strong>
          </div>
          <div style="color: #64748b; font-size: 10px; margin-top: 6px; border-top: 1px solid #1e293b; padding-top: 4px;">
            Click to inspect telemetry and scenario simulator
          </div>
        </div>
      `);

      marker.on('click', () => {
        onSelectLocation(loc);
      });

      marker.addTo(markersGroup);

      // 2. Render Hazard Zonation buffer circles for High and Severe
      if (showHazardZones && zonesGroup && (loc.risk_level === 'SEVERE' || loc.risk_level === 'HIGH')) {
        const radius = loc.risk_level === 'SEVERE' ? 5000 : 3000;
        L.circle([loc.latitude, loc.longitude], {
          radius: radius,
          color: color,
          fillColor: color,
          fillOpacity: 0.15,
          weight: 1.5,
          dashArray: '4, 6',
        }).addTo(zonesGroup);
      }
    });

    // 3. Render Historical Landslide Incidents
    if (showHistorical && histGroup && historicalEvents.length > 0) {
      historicalEvents.forEach((hist) => {
        const histIcon = L.divIcon({
          className: 'historical-incident-pin',
          html: `
            <div style="
              width: 14px;
              height: 14px;
              background: #9333ea;
              border: 1.5px solid #ffffff;
              transform: rotate(45deg);
              box-shadow: 0 2px 6px rgba(0,0,0,0.5);
            "></div>
          `,
          iconSize: [14, 14],
          iconAnchor: [7, 7],
        });

        const histMarker = L.marker([hist.latitude, hist.longitude], { icon: histIcon });
        histMarker.bindPopup(`
          <div style="font-family: inherit; font-size: 11px; min-width: 220px;">
            <div style="font-weight: bold; color: #c084fc;">HISTORICAL INCIDENT: ${escapeHtml(hist.location_name)}</div>
            <div style="color: #94a3b8; font-size: 10px;">${new Date(hist.event_date).toLocaleDateString()} | ${escapeHtml(hist.state)}</div>
            <div style="margin-top: 4px; color: #e2e8f0;">${escapeHtml(hist.infrastructure_damage || 'Debris flow catastrophe')}</div>
            <div style="margin-top: 4px; font-weight: bold; color: #f87171;">Casualties: ${hist.casualties} | Rain Trigger: ${hist.triggering_rainfall_24h || 'N/A'} mm</div>
            <div style="font-size: 9px; color: #64748b; margin-top: 4px;">Source: ${escapeHtml(hist.data_source || 'GSI Records')}</div>
          </div>
        `);
        histMarker.addTo(histGroup);
      });
    }
  }, [locations, historicalEvents, selectedLocation, showHazardZones, showHistorical]);

  // Pan to selected location
  useEffect(() => {
    if (selectedLocation && mapInstanceRef.current) {
      mapInstanceRef.current.flyTo(
        [selectedLocation.latitude, selectedLocation.longitude],
        10,
        { duration: 1.2 }
      );
    }
  }, [selectedLocation]);

  return (
    <div className="relative isolate z-0 w-full h-[620px] rounded-xl overflow-hidden border border-slate-800 shadow-2xl">
      {/* Leaflet Map Div */}
      <div ref={mapContainerRef} className="w-full h-full" />

      {/* Floating Tactical Layer Controls */}
      <div className="absolute top-4 left-4 z-[1000] flex flex-col gap-2">
        {/* Basemap Switcher */}
        <div className="flex items-center bg-[#070d19]/90 backdrop-blur p-1 rounded-lg border border-slate-800 text-xs shadow-lg">
          <button
            onClick={() => setTileMode('dark')}
            className={`px-2.5 py-1 rounded font-medium transition-colors ${
              tileMode === 'dark' ? 'bg-blue-600 text-white font-semibold' : 'text-slate-400 hover:text-white'
            }`}
          >
            Tactical Dark
          </button>
          <button
            onClick={() => setTileMode('satellite')}
            className={`px-2.5 py-1 rounded font-medium transition-colors ${
              tileMode === 'satellite' ? 'bg-blue-600 text-white font-semibold' : 'text-slate-400 hover:text-white'
            }`}
          >
            Satellite
          </button>
          <button
            onClick={() => setTileMode('topo')}
            className={`px-2.5 py-1 rounded font-medium transition-colors ${
              tileMode === 'topo' ? 'bg-blue-600 text-white font-semibold' : 'text-slate-400 hover:text-white'
            }`}
          >
            Street map
          </button>
        </div>

        {/* Layer Toggles */}
        <label className="bg-slate-950/90 rounded p-3 text-sm"><input type="checkbox" checked={showRoads} onChange={e=>setShowRoads(e.target.checked)}/> Road connectivity{showRoads&&<span className="block text-xs text-slate-300">Green open · Amber restricted · Red blocked · Grey unknown</span>}{roadError&&showRoads&&<span className="block text-amber-300">{roadError}</span>}</label>
        <label className="bg-slate-950/90 rounded p-3 text-sm"><input type="checkbox" checked={showAssets} onChange={e=>setShowAssets(e.target.checked)}/> Village / infrastructure exposure{assetError&&<span className="block text-rose-300">{assetError}</span>}</label>
        <div className="flex flex-col gap-1 bg-[#070d19]/90 backdrop-blur p-2.5 rounded-lg border border-slate-800 text-xs shadow-lg">
          <label className="flex items-center gap-2 text-slate-300 cursor-pointer hover:text-white">
            <input
              type="checkbox"
              checked={showHazardZones}
              onChange={(e) => setShowHazardZones(e.target.checked)}
              className="rounded bg-slate-800 border-slate-700 text-rose-500 focus:ring-rose-500"
            />
            <span className="flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
              <span>Hazard Impact Buffer (LHZ)</span>
            </span>
          </label>
          <label className="flex items-center gap-2 text-slate-300 cursor-pointer hover:text-white">
            <input
              type="checkbox"
              checked={showHistorical}
              onChange={(e) => setShowHistorical(e.target.checked)}
              className="rounded bg-slate-800 border-slate-700 text-purple-500 focus:ring-purple-500"
            />
            <span className="flex items-center gap-1.5">
              <HistoryIcon className="w-3.5 h-3.5 text-purple-400" />
              <span>GSI Historical Incidents</span>
            </span>
          </label>
        </div>
      </div>

      {/* Map Legend */}
      <div className="absolute bottom-4 left-4 z-[1000] bg-[#070d19]/90 backdrop-blur p-3 rounded-lg border border-slate-800 text-[11px] font-mono shadow-xl">
        <div className="font-bold text-slate-300 mb-2 uppercase tracking-wider font-sans text-xs">
          Geohazard Legend
        </div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-rose-500 border border-white pulsing-severe"></span>
            <span className="text-slate-300">Severe (&gt;75)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-orange-500 border border-white"></span>
            <span className="text-slate-300">High (50-75)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-amber-500 border border-white"></span>
            <span className="text-slate-300">Moderate (25-50)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-emerald-500 border border-white"></span>
            <span className="text-slate-300">Low (&lt;25)</span>
          </div>
          <div className="flex items-center gap-2 col-span-2 pt-1 border-t border-slate-800">
            <span className="w-2.5 h-2.5 bg-purple-500 transform rotate-45 border border-white"></span>
            <span className="text-purple-300 font-sans">Historical Landslide (GSI)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
