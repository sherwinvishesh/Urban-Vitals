

# Urban Vitals
By: Sherwin Vishesh Jathanna, Divyam Kataria, Vivien Lim

# About
This application is used to visualize, analyze, and simulate neighborhood environmental and infrastructure data using factors like safety, air quality, accessibility, and many more.
This project utilizes React frontend and a Python (FastAPI) backend.

# Goals
The purpose of this application is to collect data stats and determine the rating of the neighborhood based on multiple factors. After utilizing the data, we offer a Chatbot feature that enables advice on how to change the sustainability to make it more environmentally friendly or general questions like what certain functions or abbreviations are called.

# Strategy
We started by hardcoding the data first, then created a development tool that collects data using AI. After the AI collects the data, it transforms them into JSON. After it completes JSON, it then reacts with a fast API using React causing us to view it in production.

# Links
Slides: https://www.canva.com/design/DAGy4SSxHck/lh7Hnh_OaOkHMOMoMWLgZg/edit?utm_content=DAGy4SSxHck&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton

-----

## 🚀 Running the Application

To run this project, you will need two separate terminal windows: one for the backend API and one for the frontend web server.

### 1\. Run the Backend (Terminal 1)

The backend is a Python server built with FastAPI that serves the neighborhood data.

1.  **Navigate to the backend directory:**

    ```bash
    cd backend
    ```

2.  **Install dependencies** (it is highly recommended to use a virtual environment):

    ```bash
    pip install -r requirements.txt
    ```

3.  **Start the server:**

    ```bash
    uvicorn main:app --reload
    ```

    The API will now be running at `http://localhost:8000`.

### 2\. Run the Frontend (Terminal 2)

The frontend is a React application built with Vite that displays the map and data.

1.  **Navigate to the frontend directory:**

    ```bash
    cd frontend
    ```

2.  **Install dependencies:**

    ```bash
    npm install
    ```

3.  **Start the development server:**

    ```bash
    npm run dev
    ```

    The application will now be running at `http://localhost:5173`. Open this URL in your web browser to use Urban Vitals.