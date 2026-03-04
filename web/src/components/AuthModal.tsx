import React, { useState } from 'react';
import { Modal, Button, Form, Alert, Spinner } from 'react-bootstrap';
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

  const setField = (name: 'role' | 'major_code', value: string) => {
    setFormData(prev => ({ ...prev, [name]: value }));
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
    <Modal show={show} onHide={onHide} centered dialogClassName="auth-dialog" contentClassName="auth-card">
      <Modal.Header closeButton className="border-0 pb-0" />
      <Modal.Body className="px-4 pb-4 auth-body">
        <div className="auth-heading">{mode === 'login' ? 'Sign In' : 'Create Account'}</div>
        {error && <Alert variant="danger" className="py-2 text-center auth-error">{error}</Alert>}
        <Form onSubmit={handleSubmit}>
          <Form.Group className="mb-3">
            <Form.Label className="auth-label">Account</Form.Label>
            <Form.Control
              name="account"
              value={formData.account}
              onChange={handleChange}
              placeholder="Enter your account"
              required
              className="auth-input"
            />
          </Form.Group>
          <Form.Group className="mb-3">
            <Form.Label className="auth-label">Password</Form.Label>
            <Form.Control
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="Enter password"
              required
              className="auth-input"
            />
          </Form.Group>

          {mode === 'register' && (
            <>
              <Form.Group className="mb-3">
                <Form.Label className="auth-label">Nickname</Form.Label>
                <Form.Control
                  name="nickname"
                  value={formData.nickname}
                  onChange={handleChange}
                  placeholder="Display name"
                  required
                  className="auth-input"
                />
              </Form.Group>
              <Form.Group className="mb-3">
                <Form.Label className="auth-label">Role</Form.Label>
                <div className="auth-choice-group" role="radiogroup" aria-label="Role">
                  <button
                    type="button"
                    className={`auth-choice ${formData.role === 'student' ? 'is-selected' : ''}`}
                    role="radio"
                    aria-checked={formData.role === 'student'}
                    onClick={() => setField('role', 'student')}
                  >
                    Student
                  </button>
                  <button
                    type="button"
                    className={`auth-choice ${formData.role === 'teacher' ? 'is-selected' : ''}`}
                    role="radio"
                    aria-checked={formData.role === 'teacher'}
                    onClick={() => setField('role', 'teacher')}
                  >
                    Teacher
                  </button>
                  <button
                    type="button"
                    className={`auth-choice ${formData.role === 'admin' ? 'is-selected' : ''}`}
                    role="radio"
                    aria-checked={formData.role === 'admin'}
                    onClick={() => setField('role', 'admin')}
                  >
                    Admin
                  </button>
                </div>
              </Form.Group>

              {formData.role === 'student' && (
                <Form.Group className="mb-3">
                    <Form.Label className="auth-label">Major</Form.Label>
                    <div className="auth-choice-group auth-choice-group--stack" role="radiogroup" aria-label="Major">
                      <button
                        type="button"
                        className={`auth-choice auth-choice--stack ${formData.major_code === 'AIBA' ? 'is-selected' : ''}`}
                        role="radio"
                        aria-checked={formData.major_code === 'AIBA'}
                        onClick={() => setField('major_code', 'AIBA')}
                      >
                        <span className="auth-choice-title">MSc in AIBA</span>
                        <span className="auth-choice-sub">AIBA</span>
                      </button>
                      <button
                        type="button"
                        className={`auth-choice auth-choice--stack ${formData.major_code === 'DS' ? 'is-selected' : ''}`}
                        role="radio"
                        aria-checked={formData.major_code === 'DS'}
                        onClick={() => setField('major_code', 'DS')}
                      >
                        <span className="auth-choice-title">MSc in Data Science</span>
                        <span className="auth-choice-sub">DS</span>
                      </button>
                      <button
                        type="button"
                        className={`auth-choice auth-choice--stack ${formData.major_code === 'ADS' ? 'is-selected' : ''}`}
                        role="radio"
                        aria-checked={formData.major_code === 'ADS'}
                        onClick={() => setField('major_code', 'ADS')}
                      >
                        <span className="auth-choice-title">MSc in Applied Data Science</span>
                        <span className="auth-choice-sub">ADS</span>
                      </button>
                    </div>
                </Form.Group>
              )}
            </>
          )}

          <div className="d-grid mt-4">
            <Button
              variant="primary"
              type="submit"
              className="auth-submit py-2 text-uppercase fw-bold"
              disabled={loading}
            >
              {loading ? <Spinner size="sm" animation="border" /> : (mode === 'login' ? 'Sign In' : 'Create Account')}
            </Button>
          </div>
        </Form>

        <div className="auth-switch">
          {mode === 'login' ? (
            <span>
              Don&apos;t have an account?{' '}
              <Button
                type="button"
                variant="link"
                className="auth-link"
                onClick={() => {
                  setMode('register');
                  setError(null);
                }}
              >
                Sign up
              </Button>
            </span>
          ) : (
            <span>
              Already have an account?{' '}
              <Button
                type="button"
                variant="link"
                className="auth-link"
                onClick={() => {
                  setMode('login');
                  setError(null);
                }}
              >
                Sign in
              </Button>
            </span>
          )}
        </div>
      </Modal.Body>
    </Modal>
  );
};

export default AuthModal;
