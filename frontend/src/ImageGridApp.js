import React, { useState } from 'react';
import { Card, CardContent, Typography, Button, Switch, Slider, FormControlLabel, LinearProgress } from '@mui/material';
import { Camera, Shuffle, Printer, FolderOpen } from 'lucide-react';
import axios from 'axios';

const ImageGridApp = () => {
  const [individualImageSize, setIndividualImageSize] = useState(1000);
  const [randomizedOrder, setRandomizedOrder] = useState(true);
  const [printerPaperFormat, setPrinterPaperFormat] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);

  const handleFileSelect = (event) => {
    setSelectedFiles(event.target.files);
  };

  const handleSubmit = async () => {
    if (!selectedFiles) {
      alert('Please select files first');
      return;
    }
  
    setLoading(true);
    setProgress(0);
  
    const formData = new FormData();
    for (let i = 0; i < selectedFiles.length; i++) {
      formData.append('files[]', selectedFiles[i]);
    }
    formData.append('individualImageSize', individualImageSize);
    formData.append('randomizedOrder', randomizedOrder);
    formData.append('printerPaperFormat', printerPaperFormat);
  
    try {
      const response = await axios.post('http://127.0.0.1:5000/api/generate-grid', formData, {
        responseType: 'blob',
        timeout: 360000, // 360 seconds
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setProgress(percentCompleted);
        }
      });
  
      if (response.status === 200) {
        setProgress(100);
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', 'grid.png');
        document.body.appendChild(link);
        link.click();
      } else {
        throw new Error(`Unexpected response status: ${response.status}`);
      }
    } catch (error) {
      console.error('Error generating grid:', error);
      if (error.response) {
        console.error('Response data:', error.response.data);
        console.error('Response status:', error.response.status);
        console.error('Response headers:', error.response.headers);
        alert(`Error generating grid. Server responded with status ${error.response.status}`);
      } else if (error.request) {
        console.error('No response received:', error.request);
        alert('Error generating grid. No response received from server. Please check if the server is running and accessible.');
      } else {
        console.error('Error setting up request:', error.message);
        alert(`Error generating grid: ${error.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(to bottom right, #9c27b0, #f48fb1, #ff7043)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '1rem'
    }}>
      <Card style={{
        width: '100%',
        maxWidth: '400px',
        background: 'rgba(255, 255, 255, 0.3)',
        backdropFilter: 'blur(10px)',
        border: 'none',
        boxShadow: '0 8px 32px 0 rgba(31, 38, 135, 0.37)'
      }}>
        <CardContent>
          <Typography variant="h4" component="div" style={{ textAlign: 'center', color: 'white', marginBottom: '1rem' }}>
            Image Grid Creator
          </Typography>
          
          <div style={{ marginBottom: '1rem' }}>
            <Typography style={{ color: 'white', display: 'flex', alignItems: 'center' }}>
              <Camera style={{ marginRight: '0.5rem' }} /> Image Size: {individualImageSize}px
            </Typography>
            <Slider
              value={individualImageSize}
              onChange={(_, newValue) => setIndividualImageSize(newValue)}
              min={100}
              max={2000}
              step={100}
            />
          </div>
          
          <FormControlLabel
            control={
              <Switch
                checked={randomizedOrder}
                onChange={(e) => setRandomizedOrder(e.target.checked)}
              />
            }
            label={
              <Typography style={{ color: 'white', display: 'flex', alignItems: 'center' }}>
                <Shuffle style={{ marginRight: '0.5rem' }} /> Randomized Order
              </Typography>
            }
          />
          
          <FormControlLabel
            control={
              <Switch
                checked={printerPaperFormat}
                onChange={(e) => setPrinterPaperFormat(e.target.checked)}
              />
            }
            label={
              <Typography style={{ color: 'white', display: 'flex', alignItems: 'center' }}>
                <Printer style={{ marginRight: '0.5rem' }} /> Printer Paper Format
              </Typography>
            }
          />
          
          <div style={{ marginTop: '1rem' }}>
            <input
              type="file"
              multiple
              onChange={handleFileSelect}
              style={{ display: 'none' }}
              id="file-select"
            />
            <label htmlFor="file-select">
              <Button
                variant="outlined"
                component="span"
                fullWidth
                style={{ color: 'white', borderColor: 'white' }}
                startIcon={<FolderOpen />}
              >
                Choose Files
              </Button>
            </label>
            {selectedFiles && (
              <Typography style={{ color: 'white', marginTop: '0.5rem' }}>
                {selectedFiles.length} files selected
              </Typography>
            )}
          </div>
          
          <Button
            variant="contained"
            fullWidth
            onClick={handleSubmit}
            disabled={loading}
            style={{ marginTop: '1rem', background: 'white', color: '#9c27b0' }}
          >
            {loading ? 'Generating...' : 'Generate Image Grid'}
          </Button>

          {loading && (
            <div style={{ marginTop: '1rem' }}>
              <LinearProgress variant="determinate" value={progress} />
              <Typography style={{ color: 'white', textAlign: 'center', marginTop: '0.5rem' }}>
                {progress}% Complete
              </Typography>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default ImageGridApp;