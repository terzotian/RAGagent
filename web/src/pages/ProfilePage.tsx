import React, { useState } from 'react';
import { Container, Card, Form, Button, Row, Col, Alert, Image } from 'react-bootstrap';
import { api, getAvatarUrl } from '../services/api';
import type { User } from '../services/api';

interface ProfilePageProps {
  user: User | null;
  setUser: (user: User | null) => void;
  onLogout: () => void;
  onSwitchAccount: () => void;
}

const ProfileForm: React.FC<{
    user: User;
    setUser: (user: User | null) => void;
    onLogout: () => void;
    onSwitchAccount: () => void;
}> = ({ user, setUser, onLogout, onSwitchAccount }) => {
  const [formData, setFormData] = useState({
    nickname: user.nickname,
    role: user.role,
    major_code: user.major_code || ''
  });
  const [passData, setPassData] = useState({
    oldPassword: '',
    newPassword: ''
  });
  const [message, setMessage] = useState<{ type: 'success' | 'danger', text: string } | null>(null);

  const handleProfileUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await api.updateProfile(user.user_id, formData);
      setUser(res.user);
      setMessage({ type: 'success', text: 'Profile updated successfully!' });
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setMessage({ type: 'danger', text: error.response?.data?.detail || 'Failed to update profile' });
    }
  };

  const handlePasswordUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.updatePassword(user.user_id, {
        old_password: passData.oldPassword,
        new_password: passData.newPassword
      });
      setMessage({ type: 'success', text: 'Password updated successfully!' });
      setPassData({ oldPassword: '', newPassword: '' });
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setMessage({ type: 'danger', text: error.response?.data?.detail || 'Failed to update password' });
    }
  };

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      try {
        const res = await api.uploadAvatar(user.user_id, e.target.files[0]);
        setUser({ ...user, avatar_path: res.avatar_path });
        setMessage({ type: 'success', text: 'Avatar uploaded successfully!' });
      } catch (err: unknown) {
        const error = err as { response?: { data?: { detail?: string } } };
        setMessage({ type: 'danger', text: error.response?.data?.detail || 'Failed to upload avatar' });
      }
    }
  };

  return (
    <Container className="py-5 profile-page">
      <Row className="justify-content-center">
        <Col md={8}>
          <Card className="shadow-sm border-0 glass-surface profile-card">
            <Card.Header className="border-0 pt-4 pb-0 glass-surface-strong glass-inset-highlight profile-card-header">
              <h3 className="text-center mb-0 profile-title">User Profile</h3>
            </Card.Header>
            <Card.Body className="p-4 profile-card-body">
              {message && <Alert variant={message.type} onClose={() => setMessage(null)} dismissible>{message.text}</Alert>}

              <div className="profile-header">
                <div className="profile-avatar-area">
                  <div className="profile-avatar-stack" aria-hidden="true">
                    <div className="profile-avatar-card">
                      <div className="profile-avatar-image">
                        {user.avatar_path ? (
                          <Image
                            src={getAvatarUrl(user.avatar_path)}
                            alt="User avatar"
                            className="profile-avatar-img"
                          />
                        ) : (
                          <div className="profile-avatar-fallback">
                            {user.nickname.charAt(0).toUpperCase()}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="profile-avatar-actions">
                      <Form.Label htmlFor="avatar-upload" className="btn btn-sm btn-outline-primary mb-0 profile-btn profile-btn--avatar">
                      Change Avatar
                    </Form.Label>
                    <Form.Control
                      type="file"
                      id="avatar-upload"
                      accept="image/*"
                      className="d-none"
                      onChange={handleAvatarUpload}
                    />
                  </div>
                </div>

                <div className="profile-summary">
                  <div className="profile-name">{user.nickname}</div>
                  <div className="profile-meta">
                    <span className="profile-chip">{user.account}</span>
                    <span className="profile-chip profile-chip--accent">{user.role}</span>
                  </div>
                </div>
              </div>

              <div className="profile-sections">
                <div className="profile-section-card">
                  <div className="profile-section-title">Profile</div>
                  <Form onSubmit={handleProfileUpdate}>
                    <Row>
                      <Col md={6}>
                        <Form.Group className="mb-3">
                          <Form.Label>Account (Phone)</Form.Label>
                          <Form.Control type="text" value={user.account} disabled />
                        </Form.Group>
                      </Col>
                      <Col md={6}>
                        <Form.Group className="mb-3">
                          <Form.Label>Nickname</Form.Label>
                          <Form.Control
                            type="text"
                            value={formData.nickname}
                            onChange={(e) => setFormData({ ...formData, nickname: e.target.value })}
                          />
                        </Form.Group>
                      </Col>
                    </Row>
                    <Row>
                      <Col md={6}>
                        <Form.Group className="mb-3">
                          <Form.Label>Role</Form.Label>
                          <Form.Control type="text" value={formData.role} disabled />
                        </Form.Group>
                      </Col>
                      {formData.role === 'student' && (
                        <Col md={6}>
                          <Form.Group className="mb-3">
                            <Form.Label>Major</Form.Label>
                            <Form.Select
                              value={formData.major_code}
                              onChange={(e) => setFormData({ ...formData, major_code: e.target.value })}
                            >
                              <option value="AIBA">MSc in AIBA</option>
                              <option value="DS">MSc in Data Science</option>
                              <option value="ADS">MSc in Applied Data Science</option>
                            </Form.Select>
                          </Form.Group>
                        </Col>
                      )}
                    </Row>
                    <div className="profile-section-actions">
                      <Button variant="primary" type="submit" className="profile-btn profile-btn--primary">
                        Save Profile Changes
                      </Button>
                    </div>
                  </Form>
                </div>

                <div className="profile-section-card">
                  <div className="profile-section-title">Security</div>
                  <Form onSubmit={handlePasswordUpdate}>
                    <Row>
                      <Col md={6}>
                        <Form.Group className="mb-3">
                          <Form.Label>Old Password</Form.Label>
                          <Form.Control
                            type="password"
                            value={passData.oldPassword}
                            onChange={(e) => setPassData({ ...passData, oldPassword: e.target.value })}
                            required
                          />
                        </Form.Group>
                      </Col>
                      <Col md={6}>
                        <Form.Group className="mb-3">
                          <Form.Label>New Password (6 digits)</Form.Label>
                          <Form.Control
                            type="password"
                            value={passData.newPassword}
                            onChange={(e) => setPassData({ ...passData, newPassword: e.target.value })}
                            required
                            pattern="\d{6}"
                            title="Password must be exactly 6 digits"
                          />
                        </Form.Group>
                      </Col>
                    </Row>
                    <div className="profile-section-actions">
                      <Button variant="primary" type="submit" className="profile-btn profile-btn--primary">
                        Update Password
                      </Button>
                    </div>
                  </Form>
                </div>

                <div className="profile-actions">
                  <Button variant="outline-danger" onClick={onLogout} className="profile-btn profile-btn--danger">
                    Log Out
                  </Button>
                  <Button variant="outline-secondary" onClick={onSwitchAccount} className="profile-btn profile-btn--secondary">
                    Switch Account
                  </Button>
                </div>
              </div>

            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

const ProfilePage: React.FC<ProfilePageProps> = ({ user, setUser, onLogout, onSwitchAccount }) => {
  if (!user) {
    return <Container className="mt-5"><Alert variant="warning">Please log in to view profile.</Alert></Container>;
  }

  return (
    <ProfileForm
      key={user.user_id}
      user={user}
      setUser={setUser}
      onLogout={onLogout}
      onSwitchAccount={onSwitchAccount}
    />
  );
};

export default ProfilePage;
