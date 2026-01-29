import React, { useState, useEffect, useCallback } from 'react';
import { Container, Table, Button, Form, Modal, Alert, Spinner } from 'react-bootstrap';
import { fileApi } from '../services/api';
import type { FileItem } from '../services/api';
import { AxiosError } from 'axios';

const FilePage: React.FC = () => {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [base, setBase] = useState('lingnan');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Upload modal state
  const [showUpload, setShowUpload] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const fetchFiles = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const list = await fileApi.list(base);
      setFiles(list);
    } catch (err: unknown) {
      const error = err as AxiosError<{ detail: string }>;
      setError('Failed to load files: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  }, [base]);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  const handleDelete = async (fileName: string) => {
    if (!confirm(`Are you sure you want to delete ${fileName}?`)) return;
    try {
      await fileApi.delete(base, fileName);
      fetchFiles(); // Refresh list
    } catch (err: unknown) {
      const error = err as AxiosError<{ detail: string }>;
      alert('Delete failed: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    try {
      setUploading(true);
      await fileApi.upload(base, selectedFile);
      setShowUpload(false);
      setSelectedFile(null);
      fetchFiles();
    } catch (err: unknown) {
      const error = err as AxiosError<{ detail: string }>;
      alert('Upload failed: ' + (error.response?.data?.detail || error.message));
    } finally {
      setUploading(false);
    }
  };

  const handlePreview = async (fileName: string) => {
    try {
      const path = await fileApi.preview(base, fileName);
      alert(`File stored at: ${path}\n(Preview feature pending implementation)`);
    } catch (err: unknown) {
      const error = err as Error;
      alert('Preview failed: ' + error.message);
    }
  };

  return (
    <Container className="py-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2>Knowledge Base Files</h2>
        <div className="d-flex gap-3">
          <Form.Select
            value={base}
            onChange={(e) => setBase(e.target.value)}
            style={{ width: '150px' }}
          >
            <option value="lingnan">Lingnan</option>
            <option value="base_DS">Data Science</option>
          </Form.Select>
          <Button variant="success" onClick={() => setShowUpload(true)}>
            Upload New File
          </Button>
        </div>
      </div>

      {error && <Alert variant="danger">{error}</Alert>}

      {loading ? (
        <div className="text-center py-5">
          <Spinner animation="border" />
        </div>
      ) : (
        <Table striped bordered hover responsive>
          <thead>
            <tr>
              <th>File Name</th>
              <th>Size</th>
              <th>Uploaded At</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {files.length === 0 ? (
              <tr>
                <td colSpan={4} className="text-center text-muted">
                  No files found in this knowledge base.
                </td>
              </tr>
            ) : (
              files.map((file, idx) => (
                <tr key={idx}>
                  <td>{file.file_name}</td>
                  <td>{file.file_size}</td>
                  <td>{new Date(file.uploaded_at).toLocaleString()}</td>
                  <td>
                    <Button
                      variant="outline-primary"
                      size="sm"
                      className="me-2"
                      onClick={() => handlePreview(file.file_name)}
                    >
                      Preview
                    </Button>
                    <Button
                      variant="outline-danger"
                      size="sm"
                      onClick={() => handleDelete(file.file_name)}
                    >
                      Delete
                    </Button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </Table>
      )}

      {/* Upload Modal */}
      <Modal show={showUpload} onHide={() => setShowUpload(false)}>
        <Modal.Header closeButton>
          <Modal.Title>Upload to {base}</Modal.Title>
        </Modal.Header>
        <Modal.Body>
          <Form.Group>
            <Form.Label>Select File (PDF or TXT)</Form.Label>
            <Form.Control
              type="file"
              onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                setSelectedFile(e.target.files?.[0] || null)
              }
            />
          </Form.Group>
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={() => setShowUpload(false)}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleUpload} disabled={!selectedFile || uploading}>
            {uploading ? 'Uploading...' : 'Upload'}
          </Button>
        </Modal.Footer>
      </Modal>
    </Container>
  );
};

export default FilePage;
