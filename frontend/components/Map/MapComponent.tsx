import React, { useContext, useState, useRef, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, useMap } from 'react-leaflet';
import { LocationContext } from '@/components/utils/LocationContext';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for default marker icons in Next.js
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

interface MapComponentProps {
    setLat: (lat: number) => void;
    setLng: (lng: number) => void;
    height: string;
    width: string;
}

// Component to handle map centering
function MapController({ center }: { center: [number, number] }) {
    const map = useMap();
    React.useEffect(() => {
        map.setView(center, map.getZoom());
    }, [center, map]);
    return null;
}

// Component to handle search
function SearchControl({ onLocationSelect }: { onLocationSelect: (lat: number, lng: number) => void }) {
    const [searchQuery, setSearchQuery] = useState('');
    const [isSearching, setIsSearching] = useState(false);
    const map = useMap();

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!searchQuery.trim()) return;

        setIsSearching(true);
        try {
            // Use Nominatim (OpenStreetMap's geocoding service)
            const response = await fetch(
                `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery)}&limit=1`
            );
            const data = await response.json();

            if (data && data.length > 0) {
                const { lat, lon } = data[0];
                const latitude = parseFloat(lat);
                const longitude = parseFloat(lon);

                map.setView([latitude, longitude], 13);
                onLocationSelect(latitude, longitude);
            }
        } catch (error) {
            console.error('Search error:', error);
        } finally {
            setIsSearching(false);
        }
    };

    return null; // The actual search box is rendered outside the MapContainer
}

function MapComponent({ setLat, setLng, height, width }: MapComponentProps) {
    const { latitude, longitude } = useContext(LocationContext);
    const [searchQuery, setSearchQuery] = useState('');
    const [isSearching, setIsSearching] = useState(false);
    const mapRef = useRef<L.Map | null>(null);

    // Use user's location or default to [0, 0]
    const center: [number, number] = useMemo(
        () => [latitude ?? 0, longitude ?? 0],
        [latitude, longitude]
    );

    const [markerPosition, setMarkerPosition] = useState<[number, number]>(center);

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!searchQuery.trim()) return;

        setIsSearching(true);
        try {
            const response = await fetch(
                `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery)}&limit=1`
            );
            const data = await response.json();

            if (data && data.length > 0) {
                const { lat, lon } = data[0];
                const latitude = parseFloat(lat);
                const longitude = parseFloat(lon);

                setMarkerPosition([latitude, longitude]);
                setLat(latitude);
                setLng(longitude);

                if (mapRef.current) {
                    mapRef.current.setView([latitude, longitude], 13);
                }
            }
        } catch (error) {
            console.error('Search error:', error);
        } finally {
            setIsSearching(false);
        }
    };

    // Event handlers for draggable marker
    const eventHandlers = useMemo(
        () => ({
            dragend(e: L.DragEndEvent) {
                const marker = e.target;
                const position = marker.getLatLng();
                setMarkerPosition([position.lat, position.lng]);
                setLat(position.lat);
                setLng(position.lng);
            },
        }),
        [setLat, setLng]
    );

    return (
        <div style={{ height: `${height}`, width: '100%' }}>
            <form onSubmit={handleSearch} style={{ marginBottom: '8px' }}>
                <input
                    style={{ width: `${width}` }}
                    type="text"
                    placeholder="Search places..."
                    className="rounded-sm w-80 h-11 mt-2 text-lg p-2"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    disabled={isSearching}
                />
            </form>
            <MapContainer
                center={center}
                zoom={8}
                style={{ height: 'calc(100% - 52px)', width: '100%' }}
                ref={mapRef}
            >
                <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <Marker
                    position={markerPosition}
                    draggable={true}
                    eventHandlers={eventHandlers}
                />
                <MapController center={markerPosition} />
            </MapContainer>
        </div>
    );
}

export default MapComponent;
