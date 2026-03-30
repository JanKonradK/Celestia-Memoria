"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { useSession } from "next-auth/react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Upload, FileText, X } from "lucide-react";

const DOC_TYPES = [
  { value: "ICAO_DOC", label: "ICAO Document" },
  { value: "EASA_REG", label: "EASA Regulation" },
  { value: "AIP", label: "AIP" },
  { value: "AIP_SUP", label: "AIP Supplement" },
  { value: "UNIT_MANUAL", label: "Unit Manual" },
  { value: "LOA", label: "Letter of Agreement" },
  { value: "PROCEDURE_CHANGE", label: "Procedure Change" },
];

interface UploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function UploadDialog({ open, onOpenChange }: UploadDialogProps) {
  const { data: session } = useSession();
  const [file, setFile] = useState<File | null>(null);
  const [docType, setDocType] = useState("ICAO_DOC");
  const [aerodrome, setAerodrome] = useState("GLOBAL");
  const [effectiveDate, setEffectiveDate] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
      setError("");
      setSuccess("");
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    maxFiles: 1,
    maxSize: 100 * 1024 * 1024, // 100 MB
  });

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setError("");
    setSuccess("");

    try {
      const accessToken = (session as any)?.accessToken || "";
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "/api";

      // For local mode, send the file name as storage_path
      // The backend file watcher approach is preferred for local ingestion
      const response = await fetch(`${backendUrl}/ingest`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          storage_path: file.name,
          doc_name: file.name.replace(/\.pdf$/i, ""),
          doc_type: docType,
          aerodrome_icao: aerodrome.toUpperCase() || "GLOBAL",
          effective_date: effectiveDate || undefined,
        }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `Upload failed (${response.status})`);
      }

      setSuccess("Document queued for processing. It will be available for queries shortly.");
      setFile(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Upload Document</DialogTitle>
          <DialogDescription>
            Upload an aviation regulatory document (PDF) for indexing.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Drop zone */}
          <div
            {...getRootProps()}
            className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition-colors ${
              isDragActive
                ? "border-primary bg-primary/5"
                : "border-muted-foreground/25 hover:border-primary/50"
            }`}
          >
            <input {...getInputProps()} />
            {file ? (
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-primary" />
                <span className="text-sm font-medium">{file.name}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setFile(null);
                  }}
                  className="rounded-full p-0.5 hover:bg-muted"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            ) : (
              <>
                <Upload className="mb-2 h-8 w-8 text-muted-foreground" />
                <p className="text-sm text-muted-foreground">
                  Drop a PDF here or click to browse
                </p>
              </>
            )}
          </div>

          {/* Metadata form */}
          <div className="grid gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="docType" className="text-xs">Document Type</Label>
              <Select value={docType} onValueChange={setDocType}>
                <SelectTrigger id="docType" className="h-9 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {DOC_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value} className="text-xs">
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid gap-1.5">
              <Label htmlFor="aerodrome" className="text-xs">Aerodrome ICAO</Label>
              <Input
                id="aerodrome"
                value={aerodrome}
                onChange={(e) => setAerodrome(e.target.value)}
                placeholder="EGLL, KJFK, or GLOBAL"
                className="h-9 text-xs uppercase"
                maxLength={6}
              />
            </div>

            <div className="grid gap-1.5">
              <Label htmlFor="effectiveDate" className="text-xs">
                Effective Date (optional)
              </Label>
              <Input
                id="effectiveDate"
                type="date"
                value={effectiveDate}
                onChange={(e) => setEffectiveDate(e.target.value)}
                className="h-9 text-xs"
              />
            </div>
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}
          {success && <p className="text-sm text-green-600">{success}</p>}

          <Button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="w-full"
          >
            {uploading ? "Uploading..." : "Upload & Index"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
