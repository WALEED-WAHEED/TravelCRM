// UI Kit components for Nahd Travels
export { Button } from './button';
export { Input } from './input';
export { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from './card';
export { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from './dialog';
export { Table, TableBody, TableCaption, TableCell, TableFooter, TableHead, TableHeader, TableRow } from './table';
export { Spinner } from './spinner';
export { useToast, toast } from '@/hooks/use-toast';

// QR Viewer Component
import React from 'react';

interface QRViewerProps {
  value: string;
  size?: number;
  className?: string;
}

export function QRViewer({ value, size = 200, className }: QRViewerProps) {
  const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=${size}x${size}&data=${encodeURIComponent(value)}`;
  
  return (
    <div className={`flex items-center justify-center ${className}`}>
      <img 
        src={qrUrl} 
        alt="QR Code"
        className="border border-border rounded-md"
        width={size}
        height={size}
      />
    </div>
  );
}

// PDF Viewer Component  
interface PDFViewerProps {
  src: string;
  className?: string;
  title?: string;
}

export function PDFViewer({ src, className, title = "PDF Document" }: PDFViewerProps) {
  return (
    <iframe
      src={src}
      title={title}
      className={`w-full h-full border border-border rounded-md ${className}`}
      style={{ minHeight: '500px' }}
    />
  );
}