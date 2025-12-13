import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './components/Dashboard';
import PortfolioPage from './components/PortfolioPage';
import CandidatesPage from './components/CandidatesPage';
import TechnicalPage from './components/TechnicalPage';
import MacroAnalysisPage from './components/MacroAnalysisPage';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/portfolio" element={<PortfolioPage />} />
          <Route path="/candidates" element={<CandidatesPage />} />
          <Route path="/technical/:ticker?" element={<TechnicalPage />} />
          <Route path="/macro" element={<MacroAnalysisPage />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
