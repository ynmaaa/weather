from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
import matplotlib.pyplot as plt
import io

from ProvinceMap import province_map
from weather_mapping import weather_mapping

app = FastAPI()

BMKG_BASE_URL = "https://data.bmkg.go.id/DataMKG/MEWS/DigitalForecast/"

def parse_weather_data(xml_content):
    namespaces = {'xml': 'http://www.w3.org/XML/1998/namespace'}
    root = ET.fromstring(xml_content)
    weather_data = []

    # Mencari semua area dan parameter dengan id="weather"
    for area in root.findall(".//area"):
        area_name = area.find("name[@xml:lang='id_ID']", namespaces).text
        for parameter in area.findall(".//parameter[@id='weather']"):
            for timerange in parameter.findall("timerange"):
                datetime_str = timerange.attrib.get("datetime")
                hour = timerange.attrib.get("h")
                icon = timerange.find("value").text
                weather_description = weather_mapping.get(icon, "Unknown")
                dt = datetime.strptime(datetime_str, "%Y%m%d%H%M")
                weather_data.append({
                    "area_name": area_name,
                    "date": dt.strftime("%Y-%m-%d"),
                    "time": dt.strftime("%H:%M"),
                    "hour": hour,
                    "icon": icon,
                    "weather": weather_description
                })

    return weather_data

def create_weather_chart(weather_data):
    # Mengelompokkan data berdasarkan area_name
    area_grouped_data = {}
    for data in weather_data:
        area_name = data['area_name']
        if area_name not in area_grouped_data:
            area_grouped_data[area_name] = []
        area_grouped_data[area_name].append(data)

    plt.figure(figsize=(12, 8))
    for area_name, data in area_grouped_data.items():
        dates = [f"{d['date']} {d['time']}" for d in data]
        icons = [d['weather'] for d in data]
        plt.plot(dates, icons, marker='o', label=area_name)

    plt.title('Weather Forecast')
    plt.xlabel('Date and Time')
    plt.ylabel('Weather Condition')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.legend()
    plt.grid(True)

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()

    return buf

def get_bmkg_url(provinsi: str) -> str:
    return BMKG_BASE_URL + province_map.get(provinsi, "")

@app.get("/weather")
async def get_weather(provinsi: str = Query(..., description="Nama provinsi sesuai data BMKG")):
    url = get_bmkg_url(provinsi)
    if not url:
        raise HTTPException(status_code=400, detail="Provinsi tidak ditemukan atau tidak didukung")

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            weather_data = parse_weather_data(response.content)
            return {"weather_data": weather_data}
        else:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch data from BMKG")

# @app.get("/weather-chart")
# async def get_weather_chart(provinsi: str = Query(..., description="Nama provinsi sesuai data BMKG")):
#     url = get_bmkg_url(provinsi)
#     if not url:
#         raise HTTPException(status_code=400, detail="Provinsi tidak ditemukan atau tidak didukung")

#     async with httpx.AsyncClient() as client:
#         response = await client.get(url)
#         if response.status_code == 200:
#             weather_data = parse_weather_data(response.content)
#             buf = create_weather_chart(weather_data)
#             return StreamingResponse(buf, media_type="image/png")
#         else:
#             raise HTTPException(status_code=response.status_code, detail="Failed to fetch data from BMKG")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)