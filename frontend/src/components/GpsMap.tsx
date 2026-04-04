import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';

// Fix broken default icon paths in Vite bundler
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl:       'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl:     'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// Red marker for defect pin
const redIcon = new L.Icon({
  iconUrl:       'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
  shadowUrl:     'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize:   [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize:  [41, 41],
});

// Internal helper: recenter on coordinate change
function Recenter({ lat, lng }: { lat: number; lng: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView([lat, lng], 15, { animate: true });
  }, [lat, lng, map]);
  return null;
}

interface GpsMapProps {
  latitude: number;
  longitude: number;
  gpsStatus: string;
  riskLevel?: string;
  structureName?: string;
}

const GpsMap: React.FC<GpsMapProps> = ({
  latitude,
  longitude,
  gpsStatus,
  riskLevel = 'UNKNOWN',
  structureName = 'Inspected Asset',
}) => {
  const isReal = gpsStatus === 'real';

  return (
    <div>
      {/* GPS status badge */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '0.5rem',
        marginBottom: '0.6rem', padding: '0.45rem 0.75rem',
        borderRadius: '0.5rem',
        background: isReal ? '#dcfce7' : '#fefce8',
        border: `1px solid ${isReal ? '#86efac' : '#fde68a'}`,
        fontSize: '0.78rem', fontWeight: 700,
        color: isReal ? '#166534' : '#92400e',
      }}>
        <span>{isReal ? '📡' : '📍'}</span>
        {isReal
          ? `GPS Verified (EXIF) — ${latitude.toFixed(5)}, ${longitude.toFixed(5)}`
          : `GPS Fallback — No EXIF data (${latitude.toFixed(4)}, ${longitude.toFixed(4)})`}
      </div>

      {/* Map */}
      <div style={{
        height: 300, borderRadius: '1rem', overflow: 'hidden',
        border: '2px solid #e2e8f0',
        boxShadow: '0 4px 24px rgba(0,0,0,0.13)',
      }}>
        <MapContainer
          center={[latitude, longitude]}
          zoom={15}
          style={{ height: '100%', width: '100%' }}
          scrollWheelZoom={false}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <Recenter lat={latitude} lng={longitude} />
          <Marker position={[latitude, longitude]} icon={redIcon}>
            <Popup>
              <div style={{ fontFamily: 'Inter, system-ui', minWidth: 170 }}>
                <div style={{ fontWeight: 800, fontSize: '0.9rem', color: '#1e3a8a', marginBottom: 4 }}>
                  🏗️ {structureName}
                </div>
                <div style={{ fontSize: '0.8rem', color: '#475569', lineHeight: 1.6 }}>
                  <div><b>Risk:</b> <span style={{ color: ['CRITICAL','HIGH'].includes(riskLevel) ? '#dc2626' : '#0284c7' }}>{riskLevel}</span></div>
                  <div><b>Lat:</b> {latitude.toFixed(6)}</div>
                  <div><b>Lng:</b> {longitude.toFixed(6)}</div>
                  <div style={{ marginTop: 4, fontStyle: 'italic', color: isReal ? '#166534' : '#92400e' }}>
                    {isReal ? '✅ Verified EXIF GPS' : '⚠️ Fallback — attach GPS drone'}
                  </div>
                </div>
              </div>
            </Popup>
          </Marker>
        </MapContainer>
      </div>
    </div>
  );
};

export default GpsMap;
