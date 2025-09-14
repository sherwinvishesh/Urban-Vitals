# 🌱 Urban Vitals
**Measure what makes neighborhoods thrive**

Urban Vitals is an AI-powered sustainability platform that evaluates neighborhoods using comprehensive environmental, infrastructure, and livability metrics. Each neighborhood receives a **Green Score (1-10)** based on 13+ sustainability indicators, with real-time data integration and eco-friendly AI assistance.

![Urban Vitals Hero](https://img.shields.io/badge/Status-Hackathon_MVP-brightgreen) ![License](https://img.shields.io/badge/License-MIT-blue) ![Python](https://img.shields.io/badge/Python-3.8+-green) ![React](https://img.shields.io/badge/React-18+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-Latest-teal)

## 🎯 Features

### 🗺️ **Interactive 3D Map Visualization**
- Real-time 3D neighborhood mapping with Mapbox GL JS
- Color-coded markers based on sustainability scores
- Layer toggling for different metrics and disaster risk overlays
- Smooth transitions and hover effects

### 🤖 **Eco-Friendly AI Assistant (Tandemn Integration)**
- Powered by Tandemn's sustainable AI infrastructure
- **Real CO₂ savings tracking** - using refurbished hardware + green energy
- Contextual neighborhood analysis and comparisons
- Live token counting and environmental impact display

### 📊 **Comprehensive Scoring System**
**Core Categories:**
- **Environmental Quality**: Air quality, greenery coverage, water quality
- **Infrastructure**: Power grid reliability, road quality, cleanliness
- **Livability**: Public safety, walkability, transit access
- **Sustainability**: Renewable energy, recycling, circular economy
- **Disaster Risk (LEWC)**: Climate resilience and hazard mapping

### 🔍 **Intelligent Data Pipeline**
- **Multi-source scraping**: OpenStreetMap, government APIs, real-time sensors
- **Automated neighborhood detection** with geographic validation
- **AI-powered explanations** using Cerebras Cloud SDK
- **Live data integration** (weather, air quality, transit)

## 🏗️ Architecture

```
Urban Vitals/
├── 🌐 Frontend (React + Vite)
│   ├── Interactive Mapbox GL visualization
│   ├── AI chatbot with CO₂ tracking
│   └── Responsive design system
├── ⚡ Backend (FastAPI)
│   ├── RESTful API with comprehensive endpoints
│   ├── Neighborhood data management
│   └── AI chatbot integration
├── 🤖 Scraper Agent (Python)
│   ├── Multi-source data collection
│   ├── Geographic coordinate resolution
│   ├── Sustainability scoring algorithms
│   └── AI-powered content generation
└── 📊 Data Processing Pipeline
    ├── Real-time API integrations
    ├── Score calculation & normalization
    └── JSON data transformation
```

## 🚀 Quick Start

### Prerequisites
- **Node.js** 18+ and npm
- **Python** 3.8+ with pip
- **Mapbox Account** (free tier works)
- **API Keys**: Tandemn, Cerebras, Google Maps (optional)

### 1. Clone & Setup
```bash
git clone https://github.com/sherwinvishesh/Urban-Vitals
cd urban-vitals

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Install frontend dependencies
cd ../frontend
npm install
```

### 2. Environment Configuration
Create `.env` files:

**Backend `.env`:**
```env
TANDEMN_API_KEY=your_tandemn_key_here
CEREBRAS_API_KEY=your_cerebras_key_here
GOOGLE_API_KEY=your_google_key_here  # Optional
```

**Frontend `src/config.js`:**
```javascript
export const MAPBOX_TOKEN = 'your_mapbox_token_here';
export const API_BASE_URL = 'http://localhost:8000';
```

### 3. Launch Application
```bash
# Start backend (Terminal 1)
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Start frontend (Terminal 2)
cd frontend
npm run dev
```

Visit **http://localhost:5173** to explore Tempe neighborhoods!

## 🛠️ Data Pipeline Usage

### Generate New City Data
```bash
cd Scraper-Agent

# Method 1: Complete pipeline for any city
python run_pipeline.py "Austin, TX"

# Method 2: Individual steps
python neighbourhood_scraper.py "Boston, MA" --output-file boston_names.json
python enhanced_geocoder.py --input-file boston_names.json --output-file boston_coords.json --city-context "Boston, MA"
python data_exp_2.py --input-file boston_coords.json --output-file boston_sustainability.json
python data_exp.py --input-file boston_sustainability.json --output-file boston_personalized.json
python gs_converter.py --input-file boston_personalized.json --output-file boston_final.json
```

### Cloud Processing (Modal)
```bash
# Deploy to Modal cloud for scalable processing
modal deploy modal_pipeline.py
modal run modal_pipeline.py --city-state "Seattle, WA"
```

### Coordinate Finding (Advanced)
```bash
# High-precision geocoding with Google Maps fallback
python Coordinate_finder.py "Denver, CO"
```

## 📊 API Documentation

### Core Endpoints
- `GET /api/neighborhoods` - List all neighborhoods with scores
- `GET /api/neighborhoods/{id}` - Detailed neighborhood data
- `GET /api/neighborhoods/stats/summary` - City-wide statistics
- `POST /api/chatbot/message` - AI assistant interaction
- `GET /api/lewc` - Environmental risk/disaster data
- `GET /api/definitions` - Metric definitions & explanations

### Example Response
```json
{
  "id": 1,
  "name": "Downtown Tempe",
  "coordinates": {"lat": 33.4255, "lng": -111.9400},
  "green_score": 8.2,
  "score_variables": {
    "air_quality": 7,
    "walkability": 9,
    "public_safety": 8,
    // ... 10+ more metrics
  }
}
```

## 🌱 CO₂ Impact & Sustainability

### Real Environmental Benefits
Urban Vitals demonstrates **genuine sustainability** through:

- **🔋 Eco-Friendly AI**: Tandemn's refurbished hardware saves **1.7mg CO₂ per token**
- **♻️ Circular Economy**: Avoiding new GPU manufacturing (7,000kg CO₂ per H100)
- **🌞 Green Energy**: N. California renewable grid (0.15 vs 0.43 kgCO₂e/kWh)
- **📊 Transparency**: Live CO₂ savings tracking in chatbot interface

**Formula**: `Savings = Commercial_Embodied_Carbon + (Commercial_Power - Tandemn_Power) × Grid_Difference`

## 🔮 Future Roadmap

### Phase 1: Expansion (Next Hackathon Sprint)
- [ ] **Multi-city support** - Any US city via automated pipeline
- [ ] **Advanced disaster modeling** - Climate change projections
- [ ] **What-if simulator** - Infrastructure improvement impact
- [ ] **Community features** - User submissions & verification

### Phase 2: Intelligence
- [ ] **Predictive analytics** - Neighborhood trajectory modeling
- [ ] **Policy recommendations** - Data-driven urban planning insights
- [ ] **Real estate integration** - Property value correlations
- [ ] **Mobile application** - Native iOS/Android experience

### Phase 3: Platform
- [ ] **API marketplace** - Third-party integrations
- [ ] **Enterprise dashboard** - City planning & development tools
- [ ] **International expansion** - Global sustainability metrics
- [ ] **Research partnerships** - Academic & policy collaboration

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Run** tests and ensure data quality
4. **Commit** changes (`git commit -m 'Add amazing feature'`)
5. **Push** and create a Pull Request

### Development Guidelines
- Follow PEP 8 for Python code
- Use ESLint/Prettier for JavaScript
- Write descriptive commit messages
- Test API endpoints thoroughly
- Validate data pipeline outputs

## 📝 Technical Notes

### Known Limitations (Hackathon Scope)
- **Single city**: Currently optimized for Tempe, AZ
- **Static data**: Some metrics use simulated/averaged values
- **API quotas**: Rate-limited external data sources
- **Mobile optimization**: Responsive but not native

### Performance Considerations
- **Mapbox GL**: 60fps rendering with 200+ markers
- **API caching**: Redis recommended for production
- **Database**: PostgreSQL/MongoDB for multi-city scaling
- **CDN**: Static asset optimization needed

## 📜 License & Credits

**MIT License** - Feel free to use, modify, and distribute!

### Key Technologies
- **Frontend**: React 18, Mapbox GL JS, Axios
- **Backend**: FastAPI, Uvicorn, Python 3.8+
- **AI/ML**: Tandemn Cloud, Cerebras SDK
- **Data**: OpenStreetMap, Open-Meteo, Government APIs
- **Infrastructure**: Modal (optional), Vercel/Netlify ready

### Acknowledgments
- **OpenStreetMap** community for geographic data
- **Tandemn** for sustainable AI infrastructure  
- **Mapbox** for powerful visualization tools
- **Hackathon organizers** for the sustainability challenge

---

**Built with ❤️ for a greener future** 🌍
*By: Sherwin Vishesh Jathanna, Divyam Kataria, Vivien Lim*
*Urban Vitals - Making sustainability data accessible, actionable, and impactful for everyone.*
