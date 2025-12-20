import { createXRStore } from '@react-three/xr'

// Disable emulation to prevent module loading errors
export const xrStore = createXRStore({
    emulate: false
})
