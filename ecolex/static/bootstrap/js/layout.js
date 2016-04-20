(function() {
  window.onload = function() {
    var header = document.getElementById('site-header'),
        body = document.getElementById('site-body'),
        footer = document.getElementById('site-footer');

    function getHeight(elem) {
      elemBox = elem.getBoundingClientRect();
      return elemBox.bottom - elemBox.top;
    }
    function resize() {
      minHeight = window.innerHeight - getHeight(header) - getHeight(footer);
      body.style.minHeight = minHeight + 'px';
      console.log(minHeight);
      console.log(body);
    }
    window.addEventListener('resize', function() {
      window.clearTimeout(resize);
      window.setTimeout(resize, 200);
    });
    resize();
  }
}())
