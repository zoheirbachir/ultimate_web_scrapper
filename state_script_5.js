
  window.__ENV__ = {
    GA: "G-C1R58GKDN5",
    META: "655958734553123",
    VERSION: "3.5.24"
  };

  (function () {
    try {
      if (typeof Storage === "undefined" || typeof JSON === "undefined") return;

      var item = localStorage.getItem('ok-auth-frame');
      if (!item) return;

      var data = JSON.parse(item);
      var className = document.documentElement.className;
      var darkInClassName = className.indexOf("dark") !== -1;

      if (data && data.darkMode === true && !darkInClassName) {
        document.documentElement.className += " dark";
      }
    } catch (e) {}
  })();
