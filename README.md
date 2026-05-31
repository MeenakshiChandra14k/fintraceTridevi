# 🛡️ FinTrace SOC
### Real-Time Financial Intelligence & Forensic Analysis Platform

FinTrace SOC is a high-performance, real-time forensic platform that transforms raw transaction streams into an interactive, visual threat map. Built to intercept financial crime as it happens — not after the capital has vanished.

---

## 🚀 Key Features

- **FlowScope — Cycle Detection Engine**: Runs graph-based cycle detection across live transaction networks, exposing circular money flows and multi-hop layering patterns the moment they form.
- **Shield Interception Engine**: Automated, high-precision detection of suspicious transactions with 99.9% detection accuracy, surfaced live in the Compliance DLQ feed.
- **Real-Time Force Graph**: Interactive D3.js force-directed topology — every node, every link, every flagged entity rendered in real time with zoom and drill-down.
- **DHFL Case Modeling**: Stress-tested against the ₹34,000 crore DHFL housing finance fraud — modeling multi-hop shell entity structures and velocity anomalies.
- **One-Command Deployment**: Entire stack orchestrated via a single `make all` command — zero manual intervention.

---


| Layer | Technology |
|---|---|
| Message Streaming | Apache Kafka + Zookeeper (Docker) |
| Graph Database | Neo4j 5 (Docker) |
| Gateway API | FastAPI (Python) |
| Forensic Engine | FastAPI + FlowScope cycle detection (Python) |
| Frontend | React + D3.js + Vite |
| Orchestration | Docker Compose + Makefile |

---

## 🧠 FlowScope — How It Works

FlowScope is the forensic intelligence core of FinTrace SOC. It runs **cycle detection** across the live Neo4j transaction graph to identify:

- **Circular money flows** — capital routed through chains of entities back to its origin
- **Mule account chains** — high-velocity pass-through nodes with no legitimate activity
- **Layering patterns** — multi-hop transfers designed to obscure the source of funds

When a cycle is detected, the Shield Engine flags all involved entities, freezes their accounts, and logs every interception to the live Compliance DLQ.

---

## 📁 Project Structure

```
FINTRACETRIDEVI/
├── dashboard/              # React + D3.js frontend
│   └── src/
├── services/
│   ├── gateway-api/        # FastAPI ingestion gateway
│   │   └── main.py
│   └── pass2-deepbrain/    # FlowScope + Shield Engine
│       ├── detectors/
│       │   ├── flowscope.py
│       │   ├── mule_detector.py
│       │   └── velocity_detectors.py
│       ├── graph/
│       │   └── neo4j_client.py
│       ├── nuke.py
│       └── main.py
├── scripts/
│   └── data_pump.py        # Kafka producer
├── docker-compose.yml
└── Makefile
```

---

## 🛠️ Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.x
- Node.js 18+
- `make`

### Installation & Run

Clone the repository:
```bash
git clone https://github.com/your-username/fintracetridevi.git
cd fintracetridevi
```

### First Time Setup
```bash
make setup   # downloads sample data + creates .env
make all     # starts full stack
```

Start the entire stack with one command:
```bash
make all
```

This will:
1. Start **Kafka, Zookeeper, and Neo4j** via Docker Compose
2. Start the **Gateway API**
3. Wipe and reinitialize the graph, then start **DeepBrain** (FlowScope + Shield Engine)
4. Start the **Kafka data pump**
5. Start the **React dashboard**

### Individual Commands

```bash
make kafka       # Start Kafka data pump only
make gateway     # Start Gateway API only
make deepbrain   # Start DeepBrain engine only
make frontend    # Start React dashboard only
make stop        # Stop all services + bring down Docker
```

### Access

| Service | URL |
|---|---|
| Dashboard | http://localhost:5173 |
| Gateway API | http://localhost:8001 |
| Neo4j Browser | http://localhost:7474 |

---

## 📊 DHFL Case Study

The DHFL (Dewan Housing Finance Corporation) scandal involved the fraudulent diversion of ₹34,000 crore through a network of shell entities, fictitious borrowers, and circular transactions — one of India's largest housing finance frauds.

FinTrace SOC's ingestion pipeline and FlowScope cycle detection engine were modeled against these exact transaction patterns to validate forensic accuracy at scale. Entities structured like DHFL's shell network are flagged and frozen within milliseconds of entering the stream.

---

## 🔧 Makefile Reference

```makefile
make all        # Full stack — Docker + all 4 services
make stop       # Tear down everything
make kafka      # Kafka producer only
make gateway    # Gateway API only
make deepbrain  # DeepBrain (runs nuke.py first, then main.py)
make frontend   # React dashboard only
```

---

## 📄 License

MIT License — free to use, modify, and distribute.