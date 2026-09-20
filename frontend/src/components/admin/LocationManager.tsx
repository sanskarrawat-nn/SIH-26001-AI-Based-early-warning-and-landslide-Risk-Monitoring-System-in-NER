import React, { useState } from 'react';
import { Plus, Trash2, MapPin, CheckCircle, AlertCircle } from 'lucide-react';
import { LocationItem } from '../../types';
import { api } from '../../services/api';

interface LocationManagerProps {
  locations: LocationItem[];
  onLocationAdded: (newLoc: LocationItem) => void;
  onLocationDeleted: (locId: string) => void;
}

export const LocationManager: React.FC<LocationManagerProps> = ({
  locations,
  onLocationAdded,
  onLocationDeleted,
}) => {
  const [showAddModal, setShowAddModal] = useState(false);
  const [name, setName] = useState('');
  const [locId, setLocId] = useState('');
  const [state, setState] = useState('Assam');
  const [district, setDistrict] = useState('');
  const [lat, setLat] = useState(25.5);
  const [lon, setLon] = useState(92.5);
  const [elevation, setElevation] = useState(650);
  const [slope, setSlope] = useState(35);
  const [geology, setGeology] = useState('Weathered Sandstone & Shale');

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const nerStates = [
    'Assam',
    'Meghalaya',
    'Arunachal Pradesh',
    'Mizoram',
    'Manipur',
    'Nagaland',
    'Tripura',
    'Sikkim',
  ];

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const created = await api.createLocation({
        location_id: locId.trim(),
        name: name.trim(),
        state,
        district: district.trim(),
        latitude: lat,
        longitude: lon,
        elevation,
        slope,
        geology_type: geology,
        monitoring_status: 'ACTIVE',
      });
      onLocationAdded(created);
      setShowAddModal(false);
      setName('');
      setLocId('');
      setDistrict('');
    } catch (err: any) {
      setError(err.message || 'Failed to register location');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm(`Are you sure you want to remove '${id}' from continuous monitoring?`)) return;
    try {
      await api.deleteLocation(id);
      onLocationDeleted(id);
    } catch (err: any) {
      alert(err.message || 'Failed to remove location');
    }
  };

  return (
    <div className="p-6 rounded-xl bg-[#0c1527] border border-slate-800">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
            <MapPin className="w-4 h-4 text-blue-400" />
            <span>Monitored Vulnerable Sites Management</span>
          </h3>
          <p className="text-xs text-slate-400">
            Configure geographic, geotechnical, and telemetry telemetry nodes across the North Eastern Region.
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>Add Monitored Site</span>
        </button>
      </div>

      {/* Locations Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-900/60 text-slate-400 uppercase font-mono tracking-wider text-[11px] border-b border-slate-800">
            <tr>
              <th className="px-4 py-3">Site ID / Name</th>
              <th className="px-4 py-3">State & District</th>
              <th className="px-4 py-3">Coordinates</th>
              <th className="px-4 py-3">Slope & Elev</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-sans">
            {locations.map((loc) => (
              <tr key={loc.location_id} className="hover:bg-slate-800/30 transition-colors">
                <td className="px-4 py-3 font-mono">
                  <div className="font-semibold text-white">{loc.name}</div>
                  <div className="text-[10px] text-slate-400">{loc.location_id}</div>
                </td>
                <td className="px-4 py-3">
                  <div className="text-slate-200">{loc.district}</div>
                  <div className="text-[11px] text-slate-400">{loc.state}</div>
                </td>
                <td className="px-4 py-3 font-mono text-slate-300">
                  {loc.latitude.toFixed(4)}°N, {loc.longitude.toFixed(4)}°E
                </td>
                <td className="px-4 py-3 font-mono text-slate-300">
                  {loc.slope}° &bull; {loc.elevation}m
                </td>
                <td className="px-4 py-3">
                  <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">
                    {loc.monitoring_status}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    onClick={() => handleDelete(loc.location_id)}
                    className="p-1 rounded text-slate-400 hover:text-rose-400 hover:bg-rose-950/30 transition-colors"
                    title="Delete site"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Add Location Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#0c1527] border border-slate-700 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-sm font-bold uppercase tracking-wider text-white">Register Vulnerable Hill Sector</h3>

            {error && (
              <div className="p-2.5 rounded bg-rose-950/60 border border-rose-800 text-xs text-rose-300 flex items-center gap-1.5">
                <AlertCircle className="w-4 h-4" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleCreate} className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 font-mono mb-1">Site ID</label>
                  <input
                    type="text"
                    required
                    placeholder="LOC-AS-03"
                    value={locId}
                    onChange={(e) => setLocId(e.target.value)}
                    className="w-full px-3 py-2 rounded bg-slate-900 border border-slate-700 text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 font-mono mb-1">State</label>
                  <select
                    value={state}
                    onChange={(e) => setState(e.target.value)}
                    className="w-full px-3 py-2 rounded bg-slate-900 border border-slate-700 text-white"
                  >
                    {nerStates.map((st) => (
                      <option key={st} value={st}>{st}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 font-mono mb-1">Site Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Jatinga Highway Cut"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-3 py-2 rounded bg-slate-900 border border-slate-700 text-white"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 font-mono mb-1">District</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Dima Hasao"
                    value={district}
                    onChange={(e) => setDistrict(e.target.value)}
                    className="w-full px-3 py-2 rounded bg-slate-900 border border-slate-700 text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 font-mono mb-1">Latitude (20-32°N)</label>
                  <input
                    type="number"
                    step="0.0001"
                    required
                    value={lat}
                    onChange={(e) => setLat(parseFloat(e.target.value))}
                    className="w-full px-3 py-2 rounded bg-slate-900 border border-slate-700 text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 font-mono mb-1">Longitude (88-98°E)</label>
                  <input
                    type="number"
                    step="0.0001"
                    required
                    value={lon}
                    onChange={(e) => setLon(parseFloat(e.target.value))}
                    className="w-full px-3 py-2 rounded bg-slate-900 border border-slate-700 text-white font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 font-mono mb-1">Slope Angle (°)</label>
                  <input
                    type="number"
                    step="0.5"
                    required
                    value={slope}
                    onChange={(e) => setSlope(parseFloat(e.target.value))}
                    className="w-full px-3 py-2 rounded bg-slate-900 border border-slate-700 text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 font-mono mb-1">Elevation (meters)</label>
                  <input
                    type="number"
                    step="1"
                    required
                    value={elevation}
                    onChange={(e) => setElevation(parseFloat(e.target.value))}
                    className="w-full px-3 py-2 rounded bg-slate-900 border border-slate-700 text-white font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-400 font-mono mb-1">Lithology / Geology</label>
                <input
                  type="text"
                  value={geology}
                  onChange={(e) => setGeology(e.target.value)}
                  className="w-full px-3 py-2 rounded bg-slate-900 border border-slate-700 text-white"
                />
              </div>

              <div className="flex justify-end gap-2 pt-3">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 rounded bg-blue-600 hover:bg-blue-500 text-white font-bold"
                >
                  {submitting ? 'Registering...' : 'Register Site'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
