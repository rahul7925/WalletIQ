import React, { useState, useRef } from 'react';
import { UploadCloud, CheckCircle, AlertCircle, FileText, Sparkles, Loader2 } from 'lucide-react';
import Modal from './Modal';
import { api } from '../services/api';

export default function ReceiptScannerModal({ isOpen, onClose, onApplyData }) {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [isScanning, setIsScanning] = useState(false);
  const [extractedData, setExtractedData] = useState(null);
  const [error, setError] = useState(null);
  const fileInputRef = useRef(null);

  function handleFileSelect(selectedFile) {
    if (!selectedFile) return;
    setFile(selectedFile);
    setError(null);
    setExtractedData(null);
    if (selectedFile.type.startsWith('image/')) {
      setPreviewUrl(URL.createObjectURL(selectedFile));
    } else {
      setPreviewUrl(null);
    }
  }

  async function handleScan() {
    if (!file) {
      setError('Please select or drop a receipt image first.');
      return;
    }
    setIsScanning(true);
    setError(null);
    try {
      const data = await api.scanReceipt(file);
      setExtractedData(data);
    } catch (err) {
      setError(err.message || 'Failed to scan receipt. Please try another image.');
    } finally {
      setIsScanning(false);
    }
  }

  function handleApply() {
    if (extractedData && onApplyData) {
      onApplyData({
        amount: extractedData.amount || '',
        merchant: extractedData.merchant || '',
        category: extractedData.category || 'General',
        date: extractedData.date || new Date().toISOString().split('T')[0],
        notes: extractedData.merchant ? `Receipt scan: ${extractedData.merchant}` : 'Receipt OCR import',
      });
      handleClose();
    }
  }

  function handleClose() {
    setFile(null);
    setPreviewUrl(null);
    setExtractedData(null);
    setError(null);
    onClose();
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="AI Smart Receipt Scanner"
      maxWidth="600px"
      footer={
        <>
          <button type="button" className="btn btn-secondary" onClick={handleClose}>
            Cancel
          </button>
          {extractedData && (
            <button type="button" className="btn btn-primary" onClick={handleApply}>
              Apply to Expense
            </button>
          )}
        </>
      }
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
          Upload a receipt photo or invoice. WalletIQ Gemini Multimodal Vision automatically parses merchant, date, amounts, and category.
        </p>

        {/* Dropzone */}
        <div
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
              handleFileSelect(e.dataTransfer.files[0]);
            }
          }}
          style={{
            border: '2px dashed var(--border-color)',
            borderRadius: 'var(--radius-lg)',
            padding: '2rem 1.5rem',
            textAlign: 'center',
            cursor: 'pointer',
            background: 'rgba(255, 255, 255, 0.02)',
            transition: 'border-color 0.2s',
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*,.pdf"
            style={{ display: 'none' }}
            onChange={(e) => handleFileSelect(e.target.files[0])}
          />

          {previewUrl ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.75rem' }}>
              <img
                src={previewUrl}
                alt="Receipt Preview"
                style={{ maxHeight: '180px', maxWidth: '100%', borderRadius: 'var(--radius-md)', objectFit: 'contain' }}
              />
              <span style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
                {file?.name} (Click or drop to replace)
              </span>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
              <div style={{ padding: '0.75rem', background: 'var(--accent-gold-dim)', borderRadius: '50%', color: 'var(--accent-gold)' }}>
                <UploadCloud size={28} />
              </div>
              <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.9375rem' }}>
                Click to upload or drag & drop receipt
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Supports JPG, PNG, WEBP, PDF up to 10MB
              </span>
            </div>
          )}
        </div>

        {file && !extractedData && (
          <button
            type="button"
            className="btn btn-primary"
            style={{ width: '100%' }}
            onClick={handleScan}
            disabled={isScanning}
          >
            {isScanning ? (
              <>
                <Loader2 size={16} className="animate-spin" />
                Analyzing receipt with Gemini Vision...
              </>
            ) : (
              <>
                <Sparkles size={16} />
                Extract Receipt Data
              </>
            )}
          </button>
        )}

        {error && (
          <div
            style={{
              padding: '0.75rem 1rem',
              borderRadius: 'var(--radius-md)',
              background: 'var(--accent-red-dim)',
              border: '1px solid rgba(255, 100, 100, 0.3)',
              color: 'var(--accent-red)',
              fontSize: '0.875rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
            }}
          >
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* Extracted Details */}
        {extractedData && (
          <div
            style={{
              padding: '1.25rem',
              borderRadius: 'var(--radius-md)',
              background: 'var(--bg-elevated)',
              border: '1px solid rgba(200, 169, 110, 0.3)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent-green)', marginBottom: '1rem', fontWeight: 600, fontSize: '0.875rem' }}>
              <CheckCircle size={16} />
              <span>Receipt Extracted Successfully</span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem', fontSize: '0.875rem' }}>
              <div>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', display: 'block' }}>Merchant</span>
                <strong style={{ color: 'var(--text-primary)' }}>{extractedData.merchant || 'Unknown'}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', display: 'block' }}>Total Amount</span>
                <strong className="num-mono" style={{ color: 'var(--accent-gold)', fontSize: '1.125rem' }}>
                  ₹{Number(extractedData.amount || 0).toLocaleString()}
                </strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', display: 'block' }}>Date</span>
                <span style={{ color: 'var(--text-primary)' }}>{extractedData.date || 'N/A'}</span>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', display: 'block' }}>Category</span>
                <span className="badge badge-gold">{extractedData.category || 'General'}</span>
              </div>
              {extractedData.tax && (
                <div>
                  <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', display: 'block' }}>Tax Amount</span>
                  <span className="num-mono" style={{ color: 'var(--text-secondary)' }}>₹{extractedData.tax}</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
