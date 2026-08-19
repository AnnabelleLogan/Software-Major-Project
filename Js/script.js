if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/js/serviceworker.js')
        .then(() => console.log('Service Worker Registered'));
}