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

  const [previewData, setPreviewData] = useState<{
    show: boolean;
    title: string;
    content: string | null;
    type: 'text' | 'pdf' | 'image' | 'unknown';
    url: string | null;
  }>({
    show: false,
    title: '',
    content: null,
    type: 'unknown',
    url: null,
  });

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
      setLoading(true);
      const blob = await fileApi.preview(base, fileName);
      const type = blob.type;
      
      let previewType: 'text' | 'pdf' | 'image' | 'unknown' = 'unknown';
      let content: string | null = null;
      let url: string | null = null;

      if (type.includes('pdf')) {
        previewType = 'pdf';
        url = URL.createObjectURL(blob);
      } else if (type.includes('image')) {
        previewType = 'image';
        url = URL.createObjectURL(blob);
      } else if (type.includes('text') || type.includes('json') || type.includes('javascript') || type.includes('xml')) {
        previewType = 'text';
        content = await blob.text();
      } else {
        // 尝试作为文本读取
        try {
           const text = await blob.text();
           // 简单的启发式检查：如果包含大量乱码（这里简单判断null bytes），则可能不是文本
           if (text.indexOf('\0') === -1) {
             previewType = 'text';
             content = text;
           }
        } catch (e) {
           console.warn('Failed to read as text', e);
        }
      }

      setPreviewData({
        show: true,
        title: fileName,
        content,
        type: previewType,
        url
      });

    } catch (err: unknown) {
      const error = err as Error;
      alert('Preview failed: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const closePreview = () => {
    if (previewData.url) {
      URL.revokeObjectURL(previewData.url);
    }
    setPreviewData(prev => ({ ...prev, show: false, url: null, content: null }));
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

      {/* Preview Modal */}
      <Modal show={previewData.show} onHide={closePreview} size="lg" fullscreen={previewData.type === 'pdf' ? true : undefined}>
        <Modal.Header closeButton>
          <Modal.Title>Preview: {previewData.title}</Modal.Title>
        </Modal.Header>
        <Modal.Body className="p-0">
          {previewData.type === 'text' && previewData.content && (
            <div className="p-3 bg-light">
              <pre style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word', maxHeight: '70vh', overflow: 'auto', margin: 0 }}>
                {previewData.content}
              </pre>
            </div>
          )}
          {previewData.type === 'pdf' && previewData.url && (
            <iframe src={previewData.url} width="100%" height="100%" style={{ minHeight: '80vh', border: 'none' }} title="PDF Preview" />
          )}
          {previewData.type === 'image' && previewData.url && (
             <div className="text-center p-3">
               <img src={previewData.url} alt="Preview" style={{ maxWidth: '100%', maxHeight: '70vh' }} />
             </div>
          )}
          {previewData.type === 'unknown' && (
            <div className="p-5 text-center text-muted">
              <p>Preview not available for this file type.</p>
              {previewData.url && (
                   <Button variant="primary" href={previewData.url} download={previewData.title} as="a">Download File</Button>
               )}
            </div>
          )}
        </Modal.Body>
        <Modal.Footer>
          <Button variant="secondary" onClick={closePreview}>Close</Button>
        </Modal.Footer>
      </Modal>
    </Container>
  );
};

export default FilePage;
