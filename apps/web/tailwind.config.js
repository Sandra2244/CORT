module.exports = {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      boxShadow: {
        glow: '0 0 30px rgba(34,211,238,0.25)'
      },
      colors: {
        cort: {
          blue: '#38bdf8',
          violet: '#8b5cf6',
          cyan: '#22d3ee'
        }
      }
    }
  },
  plugins: []
}
