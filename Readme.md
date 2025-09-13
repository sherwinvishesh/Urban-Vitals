

# Urban Vitals

An application to visualize, analyze, and simulate neighborhood environmental and infrastructure data. This project consists of a React frontend and a Python (FastAPI) backend.

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