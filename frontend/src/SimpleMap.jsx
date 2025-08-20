import React, { useRef } from "react";
import { MapContainer, TileLayer } from "react-leaflet";
import "leaflet/dist/leaflet.css";

const SimpleMap = () => {
  const mapRef = useRef(null);
  const latitude = 44.494981;
  const longitude = 11.342641;

  return ( 
    // Make sure you set the height and width of the map container otherwise the map won't show
      <MapContainer center={[latitude, longitude]} zoom={13} ref={mapRef} style={{height: "100vh", width: "100vw"}}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {/* Additional map layers or components can be added here */}
      </MapContainer>
  );
};

export default SimpleMap;