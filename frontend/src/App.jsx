import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/layout/Layout';
import Home from './pages/Home';
import Dashboard from './pages/Dashboard';
import Analyze from './pages/Analyze';
import Simulation from './pages/Simulation';
import Reports from './pages/Reports';
import Budget from './pages/Budget';
import Login from './pages/Login';
import Register from './pages/Register';

const App = () => {
  return (
    <Router>
      <Routes>
        {/* Independent standalone routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Main application paths with navbar */}
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="analyze" element={<Analyze />} />
          <Route path="simulate" element={<Simulation />} />
          <Route path="reports" element={<Reports />} />
          <Route path="budget" element={<Budget />} />
        </Route>
      </Routes>
    </Router>
  );
};

export default App;
