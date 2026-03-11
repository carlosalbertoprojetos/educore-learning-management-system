$( document ).ready(function() {

    var baseUrl   = 'http://localhost:8000/';
    var deleteBtn = $('.delete-btn');
    var searchBtn = $('#search-btn');
    var searchForm = $('#search-form');
    var filter     = $('#filter');

    var themeToggle = $('#theme-toggle');

    function getPreferredTheme() {
        var stored = null;
        try {
            stored = localStorage.getItem('theme');
        } catch (err) {}
        if (stored === 'light' || stored === 'dark') {
            return stored;
        }
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return 'light';
    }

    function updateThemeLabel(theme) {
        if (!themeToggle.length) {
            return;
        }
        var nextLabel = theme === 'dark' ? themeToggle.data('label-light') : themeToggle.data('label-dark');
        if (!nextLabel) {
            nextLabel = theme === 'dark' ? 'Light' : 'Dark';
        }
        themeToggle.text(nextLabel);
        themeToggle.attr('aria-label', nextLabel);
    }

    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        try {
            localStorage.setItem('theme', theme);
        } catch (err) {}
        updateThemeLabel(theme);
    }

    if (themeToggle.length) {
        applyTheme(getPreferredTheme());
        themeToggle.on('click', function() {
            var current = document.documentElement.getAttribute('data-theme') || 'light';
            applyTheme(current === 'dark' ? 'light' : 'dark');
        });
    }

    
    $(deleteBtn).on('click', function(e) {

        e.preventDefault();

        var delLink = $(this).attr('href');
        var result = confirm('Quer deletar esta tarefa?');

        if(result) {
            window.location.href = delLink;
        }

    });

    $(searchBtn).on('click', function() {
        searchForm.submit();
    });

    $(filter).change(function() {
        var filter = $(this).val();
        window.location.href = baseUrl + '?filter=' + filter;
    });

});