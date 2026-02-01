import React, { useState, useEffect } from 'react';
import { Container, Card, Form, Button, Row, Col, Alert, Image } from 'react-bootstrap';
import { api, getAvatarUrl } from '../services/api';
import type { User } from '../services/api';

interface ProfilePageProps {
  user: User | null;
  setUser: (user: User | null) => void;
}

const ProfilePage: React.FC<ProfilePageProps> = ({ user, setUser }) => {
  const [formData, setFormData] = useState({
    nickname: '',
    gender: 'Male',
    identity: 'Student'
  });
  const [passData, setPassData] = useState({
    oldPassword: '',
    newPassword: ''
  });
  const [message, setMessage] = useState<{ type: 'success' | 'danger', text: string } | null>(null);

  useEffect(() => {
    if (user) {
      setFormData({
        nickname: user.nickname,
        gender: user.gender,
        identity: user.identity
      });
    }
  }, [user]);

  if (!user) {
    return <Container className="mt-5"><Alert variant="warning">Please log in to view profile.</Alert></Container>;
  }

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
    <Container className="py-5">
      <Row className="justify-content-center">
        <Col md={8}>
          <Card className="shadow-sm border-0 rounded-lg">
            <Card.Header className="bg-white border-0 pt-4 pb-0">
              <h3 className="text-center mb-0">User Profile</h3>
            </Card.Header>
            <Card.Body className="p-4">
              {message && <Alert variant={message.type} onClose={() => setMessage(null)} dismissible>{message.text}</Alert>}
              
              <div className="text-center mb-4">
                <div className="position-relative d-inline-block">
                  {user.avatar_path ? (
                    <Image
                      src={getAvatarUrl(user.avatar_path)}
                      roundedCircle
                      width={120}
                      height={120}
                      className="border"
                      style={{ objectFit: 'cover' }}
                    />
                  ) : (
                    <div
                      className="rounded-circle bg-primary text-white d-flex align-items-center justify-content-center mx-auto"
                      style={{ width: '120px', height: '120px', fontSize: '3rem' }}
                    >
                      {user.nickname.charAt(0).toUpperCase()}
                    </div>
                  )}
                  <div className="mt-2">
                    <Form.Label htmlFor="avatar-upload" className="btn btn-sm btn-outline-primary mb-0">
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
              </div>

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
                        onChange={(e) => setFormData({...formData, nickname: e.target.value})}
                      />
                    </Form.Group>
                  </Col>
                </Row>
                <Row>
                  <Col md={6}>
                    <Form.Group className="mb-3">
                      <Form.Label>Gender</Form.Label>
                      <Form.Select
                        value={formData.gender}
                        onChange={(e) => setFormData({...formData, gender: e.target.value})}
                      >
                        <option value="Male">Male</option>
                        <option value="Female">Female</option>
                      </Form.Select>
                    </Form.Group>
                  </Col>
                  <Col md={6}>
                    <Form.Group className="mb-3">
                      <Form.Label>Identity</Form.Label>
                      <Form.Select
                        value={formData.identity}
                        onChange={(e) => setFormData({...formData, identity: e.target.value})}
                      >
                        <option value="Student">Student</option>
                        <option value="Teacher">Teacher</option>
                      </Form.Select>
                    </Form.Group>
                  </Col>
                </Row>
                <div className="d-grid mb-4">
                  <Button variant="primary" type="submit">
                    Save Profile Changes
                  </Button>
                </div>
              </Form>

              <hr className="my-4" />
              
              <h5 className="mb-3">Change Password</h5>
              <Form onSubmit={handlePasswordUpdate}>
                <Row>
                  <Col md={6}>
                    <Form.Group className="mb-3">
                      <Form.Label>Old Password</Form.Label>
                      <Form.Control
                        type="password"
                        value={passData.oldPassword}
                        onChange={(e) => setPassData({...passData, oldPassword: e.target.value})}
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
                        onChange={(e) => setPassData({...passData, newPassword: e.target.value})}
                        required
                        pattern="\d{6}"
                        title="Password must be exactly 6 digits"
                      />
                    </Form.Group>
                  </Col>
                </Row>
                <div className="d-grid">
                  <Button variant="warning" type="submit">
                    Update Password
                  </Button>
                </div>
              </Form>

            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default ProfilePage;