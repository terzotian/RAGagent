import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, ListGroup, Table, Button, Badge, Modal, Form, Spinner, Alert } from 'react-bootstrap';
import { fileApi } from '../services/api';
import type { FileItem, Major, Course, User } from '../services/api';
import { AxiosError } from 'axios';

interface FilePageProps {
  user: User | null;
}

const FilePage: React.FC<FilePageProps> = ({ user }) => {
  // Navigation State
  const [activeTab, setActiveTab] = useState<'policies' | 'courses'>('policies');
  const [selectedMajor, setSelectedMajor] = useState<Major | null>(null);
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
  const [expandedDept, setExpandedDept] = useState(true);

  // Data State
  const [majors, setMajors] = useState<Major[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [files, setFiles] = useState<FileItem[]>([]);

  // UI State
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showSidebar, setShowSidebar] = useState(true);

  // Upload Modal State
  const [showUpload, setShowUpload] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadType, setUploadType] = useState('course_ppt'); // course_ppt or course_rubric

  // --- Initialization ---
  useEffect(() => {
    fetchMajors();
  }, []);

  // Fetch Majors (once)
  const fetchMajors = async () => {
    try {
      const data = await fileApi.listMajors();
      setMajors(data);
    } catch {
      setError('Failed to load majors');
    }
  };

  // --- Effects for Data Fetching ---
  useEffect(() => {
    if (activeTab === 'policies') {
      fetchPolicies();
    }
  }, [activeTab]);

  useEffect(() => {
    if (selectedMajor) {
      fetchCourses(selectedMajor.code);
    } else {
      setCourses([]);
    }
  }, [selectedMajor]);

  useEffect(() => {
    if (selectedCourse) {
      fetchCourseFiles(selectedCourse.course_code);
    }
  }, [selectedCourse]);


  // --- Fetch Actions ---
  const fetchPolicies = async () => {
    setLoading(true);
    setFiles([]);
    try {
      const data = await fileApi.listPolicies();
      setFiles(data);
    } catch {
      setError('Failed to load policies');
    } finally {
      setLoading(false);
    }
  };

  const fetchCourses = async (majorCode: string) => {
    // We fetch all courses, then filter locally for simplicity, or API could filter
    // For now API supports filtering by user, but let's just list all for the major
    // Actually our API listCourses takes user_id to filter for students.
    // Let's assume we want to show all courses for the selected major.
    // The current API might need adjustment if we want to list ALL courses for a major regardless of user.
    // Let's try listing all courses and filtering in JS for now if API returns all.
    // UPDATE: The API I wrote `list_courses` returns all if user_id not provided.
    // Wait, `list_courses` logic: if user_id provided AND student, filter. Else return all.
    try {
      const allCourses = await fileApi.listCourses();
      const filtered = allCourses.filter((c: Course) => c.major_code === majorCode);
      setCourses(filtered);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchCourseFiles = async (courseCode: string) => {
    setLoading(true);
    try {
      const data = await fileApi.listCourseFiles(courseCode);
      setFiles(data);
    } catch {
      setError('Failed to load course files');
    } finally {
      setLoading(false);
    }
  };

  // --- Handlers ---
  const handleDelete = async (fileId: number) => {
    if (!user) return;
    if (!confirm('Are you sure you want to delete this file?')) return;
    try {
      await fileApi.deleteFile(fileId, user.user_id);
      // Refresh
      if (activeTab === 'policies') fetchPolicies();
      else if (selectedCourse) fetchCourseFiles(selectedCourse.course_code);
    } catch (err: unknown) {
        const error = err as AxiosError<{ detail: string }>;
        alert('Delete failed: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user || !uploadFile) return;

    try {
      if (activeTab === 'policies') {
        await fileApi.uploadPolicy(user.user_id, uploadFile);
        fetchPolicies();
      } else if (selectedCourse) {
        await fileApi.uploadCourseFile(selectedCourse.course_code, user.user_id, uploadType, uploadFile);
        fetchCourseFiles(selectedCourse.course_code);
      }
      setShowUpload(false);
      setUploadFile(null);
    } catch (err: unknown) {
        const error = err as AxiosError<{ detail: string }>;
        alert('Upload failed: ' + (error.response?.data?.detail || error.message));
    }
  };

  // --- Render Helpers ---
  const canUpload = () => {
    if (!user) return false;
    if (activeTab === 'policies') return user.role === 'admin';
    if (activeTab === 'courses') return user.role === 'teacher'; // Students upload in Assignments (Chat), not here
    return false;
  };

  const canDelete = (file: FileItem) => {
    if (!user) return false;
    if (user.role === 'admin') return true;
    if (user.role === 'teacher' && ['course_ppt', 'course_rubric'].includes(file.file_type)) return true;
    return false;
  };

  return (
    <div className="d-flex h-100 w-100 overflow-hidden">
      {/* Sidebar Navigation */}
      <div
        className="bg-light border-end d-flex flex-column"
        style={{
            width: showSidebar ? '300px' : '0px',
            transition: 'width 0.3s ease',
            overflow: 'hidden',
            flexShrink: 0
        }}
      >
         <div className="p-3 border-bottom bg-white d-flex justify-content-between align-items-center">
            <h5 className="mb-0 fw-bold" style={{ color: '#B71C1C' }}>Navigation</h5>
             <Button variant="link" size="sm" className="p-0 text-secondary" onClick={() => setShowSidebar(false)}>
                 <span style={{ fontSize: '1.2rem' }}>&times;</span>
             </Button>
         </div>
         <div className="flex-grow-1 overflow-auto p-2">
            <ListGroup variant="flush">
                {/* Level 1: Lingnan (Policies) */}
                <ListGroup.Item
                    action
                    active={activeTab === 'policies'}
                    onClick={() => { setActiveTab('policies'); setSelectedMajor(null); setSelectedCourse(null); }}
                    className="border-0 rounded mb-1"
                    style={{
                        backgroundColor: activeTab === 'policies' ? 'rgba(183, 28, 28, 0.1)' : 'transparent',
                        color: activeTab === 'policies' ? '#B71C1C' : '#333',
                        fontWeight: activeTab === 'policies' ? 'bold' : 'normal'
                    }}
                >
                    Lingnan University (Policies)
                </ListGroup.Item>

                {/* Level 1: Data Science (Department) */}
                <ListGroup.Item
                    action
                    active={activeTab === 'courses' && !selectedMajor}
                    onClick={() => {
                        setExpandedDept(true);
                        setActiveTab('courses');
                        setSelectedMajor(null);
                        setSelectedCourse(null);
                    }}
                    className="border-0 rounded mb-1 d-flex justify-content-between align-items-center"
                    style={{
                        backgroundColor: (activeTab === 'courses' && !selectedMajor) ? 'rgba(183, 28, 28, 0.1)' : 'transparent',
                        color: (activeTab === 'courses' && !selectedMajor) ? '#B71C1C' : '#333',
                        fontWeight: (activeTab === 'courses' && !selectedMajor) ? 'bold' : 'normal'
                    }}
                >
                    Data Science Department
                    <span onClick={(e) => {
                        e.stopPropagation();
                        setExpandedDept(!expandedDept);
                    }} style={{ cursor: 'pointer' }}>
                        {expandedDept ? '▼' : '▶'}
                    </span>
                </ListGroup.Item>

                {/* Level 2: Majors */}
                {expandedDept && (
                    majors.length > 0 ? majors.map(major => (
                    <div key={major.code}>
                         <ListGroup.Item
                            action
                            active={selectedMajor?.code === major.code && activeTab === 'courses'}
                            onClick={() => { setActiveTab('courses'); setSelectedMajor(major); setSelectedCourse(null); }}
                            className="border-0 rounded mb-1 ps-4"
                            style={{
                                fontSize: '0.95rem',
                                backgroundColor: (selectedMajor?.code === major.code && activeTab === 'courses') ? 'rgba(183, 28, 28, 0.1)' : 'transparent',
                                color: (selectedMajor?.code === major.code && activeTab === 'courses') ? '#B71C1C' : '#333',
                                fontWeight: (selectedMajor?.code === major.code && activeTab === 'courses') ? 'bold' : 'normal'
                            }}
                        >
                            📂 {major.code} - {major.name}
                        </ListGroup.Item>

                        {/* Level 3: Courses (only if major selected) */}
                        {selectedMajor?.code === major.code && (
                            <div className="ps-3 border-start ms-4 mb-2" style={{ borderColor: '#eee' }}>
                                {courses.map(course => (
                                    <ListGroup.Item
                                        key={course.course_code}
                                        action
                                        active={selectedCourse?.course_code === course.course_code}
                                        onClick={() => setSelectedCourse(course)}
                                        className="border-0 rounded mb-1 ps-3 py-1"
                                        style={{
                                            fontSize: '0.9rem',
                                            backgroundColor: (selectedCourse?.course_code === course.course_code) ? 'rgba(183, 28, 28, 0.1)' : 'transparent',
                                            color: (selectedCourse?.course_code === course.course_code) ? '#B71C1C' : '#666',
                                            fontWeight: (selectedCourse?.course_code === course.course_code) ? 'bold' : 'normal'
                                        }}
                                    >
                                        📘 {course.course_code}
                                    </ListGroup.Item>
                                ))}
                                {courses.length === 0 && <div className="ps-3 text-muted small py-1">No courses found</div>}
                            </div>
                        )}
                    </div>
                )) : (
                    <ListGroup.Item className="border-0 ps-4 text-muted small">
                        No majors found
                    </ListGroup.Item>
                ))}
            </ListGroup>
         </div>
      </div>

      {/* Main Content */}
      <div className="flex-grow-1 d-flex flex-column h-100 overflow-hidden">
        {/* Header Bar */}
        <div className="p-3 border-bottom bg-white d-flex align-items-center justify-content-between shadow-sm" style={{ zIndex: 10 }}>
            <div className="d-flex align-items-center">
                 {!showSidebar && (
                    <Button
                        variant="link"
                        className="p-0 me-3 text-secondary"
                        onClick={() => setShowSidebar(true)}
                        title="Show Sidebar"
                    >
                        <span style={{ fontSize: '1.5rem' }}>☰</span>
                    </Button>
                )}
                <h4 className="mb-0 text-truncate" style={{ color: '#B71C1C' }}>
                    {activeTab === 'policies' && 'School Policies'}
                    {activeTab === 'courses' && !selectedMajor && 'Data Science Department'}
                    {activeTab === 'courses' && selectedMajor && !selectedCourse && `${selectedMajor.name}`}
                    {activeTab === 'courses' && selectedCourse && `${selectedCourse.course_code} - Files`}
                </h4>
            </div>

            {canUpload() && (activeTab === 'policies' || selectedCourse) && (
                <Button variant="danger" onClick={() => setShowUpload(true)} style={{ backgroundColor: '#B71C1C', borderColor: '#B71C1C' }}>
                    Upload File
                </Button>
            )}
        </div>

        {/* Scrollable Content */}
        <div className="flex-grow-1 overflow-auto p-4 bg-light">
             <Container fluid>
                {loading ? (
                    <div className="text-center py-5"><Spinner animation="border" variant="danger" /></div>
                ) : (
                    <>
                        {error && <Alert variant="danger">{error}</Alert>}

                        {/* View: List Majors */}
                        {activeTab === 'courses' && !selectedMajor && (
                            <Row xs={1} md={2} lg={3} className="g-4">
                                {majors.map(major => (
                                    <Col key={major.code}>
                                        <Card
                                            className="h-100 shadow-sm border-0 hover-card"
                                            style={{ cursor: 'pointer', transition: 'transform 0.2s' }}
                                            onClick={() => setSelectedMajor(major)}
                                            onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-5px)'}
                                            onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
                                        >
                                            <Card.Body className="d-flex flex-column align-items-center justify-content-center text-center p-4">
                                                <div className="display-4 mb-3 text-danger">📂</div>
                                                <Card.Title className="fw-bold">{major.code}</Card.Title>
                                                <Card.Text className="text-muted small">{major.name}</Card.Text>
                                            </Card.Body>
                                        </Card>
                                    </Col>
                                ))}
                                {majors.length === 0 && <p className="text-muted">No majors found.</p>}
                            </Row>
                        )}

                        {/* View: List Courses */}
                        {activeTab === 'courses' && selectedMajor && !selectedCourse && (
                             <Row xs={1} md={2} lg={3} className="g-4">
                                {courses.map(course => (
                                    <Col key={course.course_code}>
                                        <Card
                                            className="h-100 shadow-sm border-0 hover-card"
                                            style={{ cursor: 'pointer', transition: 'transform 0.2s' }}
                                            onClick={() => setSelectedCourse(course)}
                                            onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-5px)'}
                                            onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
                                        >
                                            <Card.Body className="d-flex flex-column align-items-center justify-content-center text-center p-4">
                                                <div className="display-4 mb-3 text-primary">📘</div>
                                                <Card.Title className="fw-bold">{course.course_code}</Card.Title>
                                                <Card.Text className="text-muted small">{course.name}</Card.Text>
                                            </Card.Body>
                                        </Card>
                                    </Col>
                                ))}
                                 {courses.length === 0 && <p className="text-muted">No courses found for this major.</p>}
                            </Row>
                        )}

                        {/* View: File Table */}
                        {(activeTab === 'policies' || selectedCourse) && (
                        <Card className="shadow-sm border-0">
                            <Table hover responsive className="mb-0 align-middle">
                                <thead className="bg-light">
                                    <tr>
                                        <th className="border-0">File Name</th>
                                        <th className="border-0">Type</th>
                                        <th className="border-0">Size</th>
                                        <th className="border-0">Uploaded At</th>
                                        {user && <th className="border-0">Actions</th>}
                                    </tr>
                                </thead>
                                <tbody>
                                    {files.length > 0 ? files.map(file => (
                                        <tr key={file.file_id}>
                                            <td className="fw-medium">{file.file_name}</td>
                                            <td>
                                                <Badge bg="light" text="dark" className="border">{file.file_type}</Badge>
                                            </td>
                                            <td className="text-muted small">{file.file_size}</td>
                                            <td className="text-muted small">{new Date(file.uploaded_at).toLocaleDateString()}</td>
                                            {user && (
                                                <td>
                                                    {canDelete(file) && (
                                                        <Button
                                                            variant="outline-danger"
                                                            size="sm"
                                                            onClick={() => handleDelete(file.file_id)}
                                                            className="rounded-pill px-3"
                                                        >
                                                            Delete
                                                        </Button>
                                                    )}
                                                </td>
                                            )}
                                        </tr>
                                    )) : (
                                        <tr>
                                            <td colSpan={5} className="text-center py-5 text-muted">
                                                <div className="mb-2" style={{ fontSize: '2rem' }}>📭</div>
                                                No files found in this category.
                                            </td>
                                        </tr>
                                    )}
                                </tbody>
                            </Table>
                        </Card>
                        )}
                    </>
                )}
             </Container>
        </div>
      </div>

      {/* Upload Modal */}
      <Modal show={showUpload} onHide={() => setShowUpload(false)} centered>
        <Modal.Header closeButton className="border-0">
            <Modal.Title className="fw-bold text-danger">Upload File</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleUploadSubmit}>
            <Modal.Body>
                {activeTab === 'courses' && (
                    <Form.Group className="mb-3">
                        <Form.Label>File Type</Form.Label>
                        <Form.Select
                            value={uploadType}
                            onChange={(e) => setUploadType(e.target.value)}
                        >
                            <option value="course_ppt">Course PPT</option>
                            <option value="course_rubric">Course Rubric/Syllabus</option>
                        </Form.Select>
                    </Form.Group>
                )}
                <Form.Group className="mb-3">
                    <Form.Label>Select File</Form.Label>
                    <div className="p-4 border border-dashed rounded text-center bg-light">
                        <Form.Control
                            type="file"
                            required
                            onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
                              if (e.target.files && e.target.files.length > 0) {
                                setUploadFile(e.target.files[0]);
                              }
                            }}
                            className="mb-2"
                        />
                        <small className="text-muted">Supported formats: PDF, DOCX, TXT, PPTX</small>
                    </div>
                </Form.Group>
            </Modal.Body>
            <Modal.Footer className="border-0">
                <Button variant="light" onClick={() => setShowUpload(false)}>Cancel</Button>
                <Button variant="danger" type="submit" disabled={!uploadFile} style={{ backgroundColor: '#B71C1C', borderColor: '#B71C1C' }}>
                    Upload
                </Button>
            </Modal.Footer>
        </Form>
      </Modal>
    </div>
  );

};

export default FilePage;
