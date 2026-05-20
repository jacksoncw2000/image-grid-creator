import React, { useMemo, useRef, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Container,
  Divider,
  FormControlLabel,
  LinearProgress,
  Paper,
  Slider,
  Stack,
  Switch,
  Tooltip,
  Typography,
} from '@mui/material';
import {
  Camera,
  CheckCircle2,
  Download,
  FolderOpen,
  Image as ImageIcon,
  Maximize2,
  Printer,
  Puzzle,
  RotateCcw,
  Shuffle,
} from 'lucide-react';
import { createImageGrid, readApiErrorMessage } from './api';
import {
  ACCEPTED_IMAGE_EXTENSIONS,
  DEFAULT_BACKEND_UPLOAD_LIMIT_BYTES,
  downloadBlob,
  filenameFromHeaders,
  fileStats,
  filesFromInput,
  formatBytes,
} from './fileUtils';
import './ImageGridApp.css';

const DEFAULT_SETTINGS = {
  individualImageSize: 1000,
  randomizedOrder: true,
  printerPaperFormat: false,
  stretchToSquare: false,
  collageLayout: false,
};

const ImageGridApp = () => {
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [phase, setPhase] = useState('idle');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');
  const fileInputRef = useRef(null);

  const selectedStats = useMemo(() => fileStats(selectedFiles), [selectedFiles]);
  const isWorking = phase !== 'idle';
  const isOverDefaultUploadLimit =
    selectedStats.totalBytes > DEFAULT_BACKEND_UPLOAD_LIMIT_BYTES;

  const updateSetting = (key, value) => {
    setSettings((current) => {
      if (key === 'collageLayout' && value) {
        return {
          ...current,
          collageLayout: true,
          printerPaperFormat: false,
          stretchToSquare: false,
        };
      }

      if ((key === 'printerPaperFormat' || key === 'stretchToSquare') && value) {
        return {
          ...current,
          [key]: true,
          collageLayout: false,
        };
      }

      return { ...current, [key]: value };
    });
  };

  const handleFileSelect = (event) => {
    setSelectedFiles(filesFromInput(event.target.files));
    setErrorMessage('');
    setSuccessMessage('');
    setUploadProgress(0);
  };

  const clearSelection = () => {
    setSelectedFiles([]);
    setErrorMessage('');
    setSuccessMessage('');
    setUploadProgress(0);

    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSubmit = async () => {
    if (!selectedFiles.length) {
      setErrorMessage('Select at least one image.');
      return;
    }

    setPhase('uploading');
    setUploadProgress(0);
    setErrorMessage('');
    setSuccessMessage('');

    try {
      const response = await createImageGrid({
        files: selectedFiles,
        settings,
        onUploadProgress: (progressEvent) => {
          if (!progressEvent.total) {
            return;
          }

          const percent = Math.min(
            100,
            Math.round((progressEvent.loaded * 100) / progressEvent.total)
          );
          setUploadProgress(percent);

          if (percent >= 100) {
            setPhase('generating');
          }
        },
      });

      const filename = filenameFromHeaders(response.headers);
      downloadBlob(response.data, filename);
      setSuccessMessage(`Downloaded ${filename}.`);
      setUploadProgress(100);
    } catch (error) {
      setErrorMessage(await readApiErrorMessage(error));
    } finally {
      setPhase('idle');
    }
  };

  const progressLabel =
    phase === 'generating' ? 'Creating grid...' : `Uploading ${uploadProgress}%`;

  return (
    <main className="grid-app-shell">
      <Container maxWidth="md" className="grid-app-container">
        <Paper elevation={0} className="grid-tool-panel">
          <Stack spacing={3}>
            <Box className="grid-tool-header">
              <Box>
                <Typography variant="h3" component="h1" className="grid-tool-title">
                  Image Grid Creator
                </Typography>
              </Box>
              <Chip
                icon={<ImageIcon size={16} />}
                label={`${selectedStats.count} selected`}
                className="grid-count-chip"
              />
            </Box>

            <Divider />

            <Box>
              <Stack
                direction="row"
                alignItems="center"
                justifyContent="space-between"
                spacing={2}
                className="setting-row"
              >
                <Stack direction="row" spacing={1.25} alignItems="center">
                  <Camera size={20} />
                  <Typography className="setting-label">Cell size</Typography>
                </Stack>
                <Typography className="setting-value">
                  {settings.individualImageSize}px
                </Typography>
              </Stack>
              <Slider
                aria-label="Cell size"
                value={settings.individualImageSize}
                onChange={(_, value) => updateSetting('individualImageSize', value)}
                min={100}
                max={3000}
                step={50}
                valueLabelDisplay="auto"
              />
            </Box>

            <Box className="switch-grid">
              <FormControlLabel
                className="switch-control"
                control={
                  <Switch
                    checked={settings.randomizedOrder}
                    onChange={(event) =>
                      updateSetting('randomizedOrder', event.target.checked)
                    }
                  />
                }
                label={
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Shuffle size={19} />
                    <span>Randomized order</span>
                  </Stack>
                }
              />

              <FormControlLabel
                className="switch-control"
                control={
                  <Switch
                    checked={settings.printerPaperFormat}
                    onChange={(event) =>
                      updateSetting('printerPaperFormat', event.target.checked)
                    }
                  />
                }
                label={
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Printer size={19} />
                    <span>Printer shape</span>
                  </Stack>
                }
              />

              <FormControlLabel
                className="switch-control"
                control={
                  <Switch
                    checked={settings.stretchToSquare}
                    onChange={(event) =>
                      updateSetting('stretchToSquare', event.target.checked)
                    }
                  />
                }
                label={
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Maximize2 size={19} />
                    <span>Stretch squares</span>
                  </Stack>
                }
              />

              <FormControlLabel
                className="switch-control"
                control={
                  <Switch
                    checked={settings.collageLayout}
                    onChange={(event) =>
                      updateSetting('collageLayout', event.target.checked)
                    }
                  />
                }
                label={
                  <Stack direction="row" spacing={1} alignItems="center">
                    <Puzzle size={19} />
                    <span>Collage layout</span>
                  </Stack>
                }
              />
            </Box>

            <Stack spacing={1.5}>
              <input
                ref={fileInputRef}
                id="file-select"
                type="file"
                multiple
                accept={ACCEPTED_IMAGE_EXTENSIONS.join(',')}
                onChange={handleFileSelect}
                className="hidden-file-input"
              />
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
                <label htmlFor="file-select" className="choose-file-label">
                  <Button
                    variant="outlined"
                    component="span"
                    startIcon={<FolderOpen size={18} />}
                    fullWidth
                  >
                    Choose files
                  </Button>
                </label>
                <Tooltip title="Clear selected files">
                  <span>
                    <Button
                      variant="text"
                      color="inherit"
                      startIcon={<RotateCcw size={17} />}
                      onClick={clearSelection}
                      disabled={isWorking || !selectedFiles.length}
                      fullWidth
                    >
                      Clear
                    </Button>
                  </span>
                </Tooltip>
              </Stack>

              <Typography className="file-summary">
                {selectedStats.count
                  ? `${selectedStats.count} files, ${formatBytes(selectedStats.totalBytes)}`
                  : 'No files selected'}
              </Typography>
            </Stack>

            {isOverDefaultUploadLimit && (
              <Alert severity="warning">
                Selected files total {formatBytes(selectedStats.totalBytes)}. The default
                backend upload limit is {formatBytes(DEFAULT_BACKEND_UPLOAD_LIMIT_BYTES)}.
              </Alert>
            )}

            {errorMessage && <Alert severity="error">{errorMessage}</Alert>}
            {successMessage && (
              <Alert icon={<CheckCircle2 size={20} />} severity="success">
                {successMessage}
              </Alert>
            )}

            <Button
              variant="contained"
              size="large"
              startIcon={<Download size={19} />}
              onClick={handleSubmit}
              disabled={isWorking || !selectedFiles.length}
              className="create-button"
            >
              {isWorking ? 'Working...' : 'Create grid'}
            </Button>

            {isWorking && (
              <Box>
                <LinearProgress
                  variant={phase === 'generating' ? 'indeterminate' : 'determinate'}
                  value={uploadProgress}
                />
                <Typography className="progress-label">{progressLabel}</Typography>
              </Box>
            )}
          </Stack>
        </Paper>
      </Container>
    </main>
  );
};

export default ImageGridApp;
