import React, { useState } from 'react';
import { Modal, Button, Form, Nav, Alert, Spinner } from 'react-bootstrap';
import { api } from '../services/api';
import type { User } from '../services/api';

interface AuthModalProps {
  show: boolean;
  onHide: () => void;
  onLoginSuccess: (user: User) => void;
}

const AuthModal: React.FC<AuthModalProps> = ({ show, onHide, onLoginSuccess }) => {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<React.ReactNode | null>(null);

  const [formData, setFormData] = useState({
    account: '',
    password: '',
    nickname: '',
    role: 'student',
    major_code: 'AIBA'
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Frontend Validation
    if (mode === 'register') {
      const phoneRegex = /^\d{11}$/;
      const passwordRegex = /^\d{6}$/;
      const nicknameRegex = /^[\u4e00-\u9fa5a-zA-Z]+$/;

      if (!phoneRegex.test(formData.account)) {
        setError('Account must be an 11-digit phone number');
        return;
      }
      if (!passwordRegex.test(formData.password)) {
        setError('Password must be exactly 6 digits');
        return;
      }
      if (!nicknameRegex.test(formData.nickname)) {
        setError('Nickname must contain only English or Chinese characters');
        return;
      }
    }

    setLoading(true);

    try {
      if (mode === 'login') {
        const res = await api.login({
          account: formData.account,
          password: formData.password
        });
        onLoginSuccess(res.user);
        onHide();
      } else {
        await api.register({
            account: formData.account,
            password: formData.password,
            nickname: formData.nickname,
            role: formData.role,
            major_code: formData.role === 'student' ? formData.major_code : undefined
        });
        setMode('login');
        setError(null);
        alert('Registration successful! Please login.');
      }
    } catch (err: unknown) {
      console.error(err);
      const apiError = err as { response?: { data?: { detail?: string | Array<{ msg: string }> } } };

      if (apiError.response?.data?.detail) {
        const detail = apiError.response.data.detail;
        if (typeof detail === 'string' && detail === 'Account already exists') {
            setError(
                <span>
                    Account already exists. <span className="text-decoration-underline" style={{cursor: 'pointer', fontWeight: 'bold'}} onClick={() => {
                        setMode('login');
                        setError(null);
                    }}>Go to Login</span>
                </span>
            );
        } else if (Array.isArray(detail)) {
            // Handle Pydantic validation errors (array of objects)
            setError(detail.map(e => e.msg).join(', '));
        } else {
            // Handle standard HTTP exceptions (string)
            setError(detail);
        }
      } else {
        setError('An error occurred. Please check your connection or try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal show={show} onHide={onHide} centered contentClassName="auth-modal-content">
      <style>{`
        .auth-modal-content {
          background: rgba(255, 255, 255, 0.85);
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.3);
          box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
          border-radius: 15px;
        }
        .auth-nav .nav-link {
          color: #666;
          border: none;
          background: transparent;
          font-weight: 600;
          transition: all 0.3s ease;
        }
        .auth-nav .nav-link.active {
          color: #0d6efd;
          background: transparent;
          border-bottom: 2px solid #0d6efd;
        }
        .avant-garde-btn {
          background: linear-gradient(45deg, #0d6efd, #0dcaf0);
          border: none;
          transition: transform 0.2s;
        }
        .avant-garde-btn:hover {
          transform: scale(1.02);
          background: linear-gradient(45deg, #0b5ed7, #0aa2c0);
        }
      `}</style>
      <Modal.Header closeButton className="border-0">
        <Nav className="w-100 justify-content-center auth-nav" variant="tabs" activeKey={mode}>
          <Nav.Item>
            <Nav.Link eventKey="login" onClick={() => setMode('login')}>Login</Nav.Link>
          </Nav.Item>
          <Nav.Item>
            <Nav.Link eventKey="register" onClick={() => setMode('register')}>Register</Nav.Link>
          </Nav.Item>
        </Nav>
      </Modal.Header>
      <Modal.Body className="px-4 pb-4">
        {error && <Alert variant="danger" className="py-2 text-center">{error}</Alert>}
        <Form onSubmit={handleSubmit}>
          <Form.Group className="mb-3">
            <Form.Label>Account</Form.Label>
            <Form.Control
              name="account"
              value={formData.account}
              onChange={handleChange}
              placeholder="Enter your account"
              required
            />
          </Form.Group>
          <Form.Group className="mb-3">
            <Form.Label>Password</Form.Label>
            <Form.Control
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="Enter password"
              required
            />
          </Form.Group>

          {mode === 'register' && (
            <>
              <Form.Group className="mb-3">
                <Form.Label>Nickname</Form.Label>
                <Form.Control
                  name="nickname"
                  value={formData.nickname}
                  onChange={handleChange}
                  placeholder="Display name"
                  required
                />
              </Form.Group>
              <Form.Group className="mb-3">
                <Form.Label>Role</Form.Label>
                <Form.Select name="role" value={formData.role} onChange={handleChange}>
                  <option value="student">Student</option>
                  <option value="teacher">Teacher</option>
                  <option value="admin">Admin</option>
                </Form.Select>
              </Form.Group>

              {formData.role === 'student' && (
                <Form.Group className="mb-3">
                    <Form.Label>Major</Form.Label>
                    <Form.Select name="major_code" value={formData.major_code} onChange={handleChange}>
                    <option value="AIBA">MSc in AIBA</option>
                    <option value="DS">MSc in Data Science</option>
                    <option value="ADS">MSc in Applied Data Science</option>
                    </Form.Select>
                </Form.Group>
              )}
            </>
          )}

          <div className="d-grid mt-4">
            <Button
              variant="primary"
              type="submit"
              className="avant-garde-btn py-2 text-uppercase fw-bold"
              disabled={loading}
            >
              {loading ? <Spinner size="sm" animation="border" /> : (mode === 'login' ? 'Sign In' : 'Create Account')}
            </Button>
          </div>
        </Form>
      </Modal.Body>
    </Modal>
  );
};

export default AuthModal;
