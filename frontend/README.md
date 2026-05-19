# Image Grid Creator Frontend

React client for selecting images, configuring grid output, and downloading the
generated PNG from the Flask backend. The file picker accepts common image
formats, including HEIC/HEIF.

## Scripts

```bash
npm start
npm test -- --watchAll=false
npm run build
```

By default the client calls `http://127.0.0.1:5000`. Set
`REACT_APP_API_BASE_URL` when the backend runs somewhere else.
