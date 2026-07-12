import react from '@vitejs/plugin-react';
// base "./" = assets relativos (o artefato roda numa sub-rota /a/<projectId>/<slug>/).
export default { base: './', plugins: [react()] };
