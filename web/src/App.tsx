import React, { useState } from 'react';
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Link,
  Navigate,
  useLocation,
} from 'react-router-dom';
import { Navbar, Container, Nav, Image } from 'react-bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';
import ChatPage from './pages/ChatPage';
import FilePage from './pages/FilePage';
import ProfilePage from './pages/ProfilePage';
import AuthModal from './components/AuthModal';
import { getAvatarUrl } from './services/api';
import type { User } from './services/api';

const Layout: React.FC = () => {
  const location = useLocation();
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [user, setUser] = useState<User | null>(null);

  const handleLoginSuccess = (loggedInUser: User) => {
    setUser(loggedInUser);
    setShowAuthModal(false);
  };

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
            <Nav>
              {user ? (
                <div className="d-flex align-items-center">
                  <span className="me-2 text-secondary">{user.nickname}</span>
                  <Link to="/profile" className="text-decoration-none">
                    {user.avatar_path ? (
                      <Image
                        src={getAvatarUrl(user.avatar_path)}
                        roundedCircle
                        width={40}
                        height={40}
                        className="border"
                        style={{ objectFit: 'cover', cursor: 'pointer' }}
                        title={user.identity}
                      />
                    ) : (
                      <div
                        className="rounded-circle bg-primary text-white d-flex align-items-center justify-content-center"
                        style={{ width: '40px', height: '40px', cursor: 'pointer', fontSize: '1.2rem' }}
                        title={user.identity}
                      >
                        {user.nickname.charAt(0).toUpperCase()}
                      </div>
                    )}
                  </Link>
                </div>
              ) : (
                <div
                  className="rounded-circle bg-secondary text-white d-flex align-items-center justify-content-center"
                  style={{ width: '40px', height: '40px', cursor: 'pointer' }}
                  onClick={() => setShowAuthModal(true)}
                  title="Login / Register"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" viewBox="0 0 16 16">
                    <path d="M11 6a3 3 0 1 1-6 0 3 3 0 0 1 6 0z"/>
                    <path fillRule="evenodd" d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8zm8-7a7 7 0 0 0-5.468 11.37C3.242 11.226 4.805 10 8 10s4.757 1.225 5.468 2.37A7 7 0 0 0 8 1z"/>
                  </svg>
                </div>
              )}
            </Nav>
          </Navbar.Collapse>
        </Container>
      </Navbar>

      <AuthModal
        show={showAuthModal}
        onHide={() => setShowAuthModal(false)}
        onLoginSuccess={handleLoginSuccess}
      />

      <div
        className="flex-grow-1 position-relative"
        style={{ backgroundColor: '#f7f7f8', overflow: 'hidden' }}
      >
        <Routes>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="/chat" element={<ChatPage user={user} />} />
          <Route path="/files" element={<FilePage />} />
          <Route path="/profile" element={<ProfilePage user={user} setUser={setUser} />} />
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
