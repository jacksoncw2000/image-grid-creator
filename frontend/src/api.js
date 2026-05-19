import axios from 'axios';

export const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://127.0.0.1:5000';

export const createImageGrid = ({ files, settings, onUploadProgress }) => {
  const formData = new FormData();

  files.forEach((file) => {
    formData.append('files[]', file);
  });

  formData.append('individualImageSize', settings.individualImageSize);
  formData.append('randomizedOrder', settings.randomizedOrder);
  formData.append('printerPaperFormat', settings.printerPaperFormat);
  formData.append('stretchToSquare', settings.stretchToSquare);

  return axios.post(`${API_BASE_URL}/api/create-grid`, formData, {
    responseType: 'blob',
    timeout: 15 * 60 * 1000,
    onUploadProgress,
  });
};

export const readApiErrorMessage = async (error) => {
  const status = error.response?.status;
  const payload = await parseErrorPayload(error.response?.data);
  const serverMessage = payload?.error?.message || payload?.message || payload?.error;

  if (serverMessage) {
    return serverMessage;
  }

  if (status === 413) {
    return 'Upload is too large for the backend limit.';
  }

  if (status) {
    return `Server responded with status ${status}.`;
  }

  if (error.request) {
    return `No response from the backend at ${API_BASE_URL}.`;
  }

  return error.message || 'Could not create the image grid.';
};

const parseErrorPayload = async (data) => {
  if (!data) {
    return null;
  }

  if (typeof Blob !== 'undefined' && data instanceof Blob) {
    const text = await data.text();
    if (!text) {
      return null;
    }

    try {
      return JSON.parse(text);
    } catch {
      return { error: text };
    }
  }

  if (typeof data === 'string') {
    try {
      return JSON.parse(data);
    } catch {
      return { error: data };
    }
  }

  return data;
};
