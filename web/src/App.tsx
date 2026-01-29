import React from 'react';
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Link,
  Navigate,
  useLocation,
} from 'react-router-dom';
import { Navbar, Container, Nav } from 'react-bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';
import ChatPage from './pages/ChatPage';
import FilePage from './pages/FilePage';

const Layout: React.FC = () => {
  const location = useLocation();

  return (
    <div className="d-flex flex-column vh-100">
      <Navbar
        bg="white"
        variant="light"
        expand="lg"
        className="border-bottom shadow-sm"
        style={{ zIndex: 10 }}
      >
        <Container fluid>
          <Navbar.Brand as={Link} to="/chat" className="fw-bold text-primary">
            AgentRAG
          </Navbar.Brand>
          <Navbar.Toggle aria-controls="basic-navbar-nav" />
          <Navbar.Collapse id="basic-navbar-nav">
            <Nav className="me-auto">
              <Nav.Link as={Link} to="/chat" active={location.pathname === '/chat'}>
                Chat
              </Nav.Link>
              <Nav.Link as={Link} to="/files" active={location.pathname === '/files'}>
                Files
              </Nav.Link>
            </Nav>
          </Navbar.Collapse>
        </Container>
      </Navbar>

      <div
        className="flex-grow-1 position-relative"
        style={{ backgroundColor: '#f7f7f8', overflow: 'hidden' }}
      >
        <Routes>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/files" element={<FilePage />} />
        </Routes>
      </div>
    </div>
  );
};

const App: React.FC = () => {
  return (
    <Router>
      <Layout />
    </Router>
  );
};

export default App;
