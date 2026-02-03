import React, { useState } from 'react';
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Link,
  Navigate,
  useLocation,
} from 'react-router-dom';
import { Navbar, Container, Nav, Image, Dropdown } from 'react-bootstrap';
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
  const [base, setBase] = useState('lingnan');
  const [language, setLanguage] = useState<'en' | 'zh-cn' | 'zh-tw'>('en');

  const handleLoginSuccess = (loggedInUser: User) => {
    setUser(loggedInUser);
    setShowAuthModal(false);
  };

  return (
    <div className="d-flex flex-column vh-100">
      <Navbar
        variant="light"
        expand="lg"
        className="border-bottom shadow-sm py-3 navbar-gradient"
        style={{ zIndex: 10, minHeight: '110px' }}
      >
        <Container fluid>
          <Navbar.Brand as={Link} to="/chat" className="fw-bold text-primary navbar-brand-dynamic d-flex align-items-center">
            <Image
              src="/logo.jpg"
              alt="Lingnan University"
              style={{ height: '70px', objectFit: 'contain' }}
            />
          </Navbar.Brand>
          <Navbar.Toggle aria-controls="basic-navbar-nav" />
          <Navbar.Collapse id="basic-navbar-nav">
            <Nav className="me-auto">
              <Nav.Link as={Link} to="/chat" active={location.pathname === '/chat'} className={`nav-link-dynamic ${location.pathname === '/chat' ? 'active' : ''}`}>
                Chat
              </Nav.Link>
              <Nav.Link as={Link} to="/files" active={location.pathname === '/files'} className={`nav-link-dynamic ${location.pathname === '/files' ? 'active' : ''}`}>
                Files
              </Nav.Link>
            </Nav>
            <div className="d-flex gap-3 me-3 align-items-center">
              <Dropdown>
                <Dropdown.Toggle
                  variant="custom"
                  id="dropdown-base"
                  className="custom-dropdown-toggle"
                >
                  {base === 'lingnan' ? 'Lingnan' : 'Data Science'}
                </Dropdown.Toggle>
                <Dropdown.Menu className="custom-dropdown-menu">
                  <Dropdown.Item
                    onClick={() => setBase('lingnan')}
                    className="custom-dropdown-item"
                    active={base === 'lingnan'}
                  >
                    Lingnan
                  </Dropdown.Item>
                  <Dropdown.Item
                    onClick={() => setBase('base_DS')}
                    className="custom-dropdown-item"
                    active={base === 'base_DS'}
                  >
                    Data Science
                  </Dropdown.Item>
                </Dropdown.Menu>
              </Dropdown>

              <Dropdown>
                <Dropdown.Toggle
                  variant="custom"
                  id="dropdown-language"
                  className="custom-dropdown-toggle"
                >
                  {language === 'zh-cn' ? '简体中文' : language === 'en' ? 'English' : '繁体中文'}
                </Dropdown.Toggle>
                <Dropdown.Menu className="custom-dropdown-menu">
                  <Dropdown.Item
                    onClick={() => setLanguage('zh-cn')}
                    className="custom-dropdown-item"
                    active={language === 'zh-cn'}
                  >
                    简体中文
                  </Dropdown.Item>
                  <Dropdown.Item
                    onClick={() => setLanguage('en')}
                    className="custom-dropdown-item"
                    active={language === 'en'}
                  >
                    English
                  </Dropdown.Item>
                  <Dropdown.Item
                    onClick={() => setLanguage('zh-tw')}
                    className="custom-dropdown-item"
                    active={language === 'zh-tw'}
                  >
                    繁体中文
                  </Dropdown.Item>
                </Dropdown.Menu>
              </Dropdown>
            </div>
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
                <Image
                  src="/guest_logo.png"
                  roundedCircle
                  width={40}
                  height={40}
                  className="border"
                  style={{ objectFit: 'cover', cursor: 'pointer' }}
                  onClick={() => setShowAuthModal(true)}
                  title="Login / Register"
                />
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
        <div key={location.pathname} className="route-view page-enter">
          <Routes>
            <Route path="/" element={<Navigate to="/chat" replace />} />
            <Route path="/chat" element={<ChatPage user={user} base={base} language={language} />} />
            <Route path="/files" element={<FilePage />} />
            <Route path="/profile" element={<ProfilePage user={user} setUser={setUser} />} />
          </Routes>
        </div>
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
