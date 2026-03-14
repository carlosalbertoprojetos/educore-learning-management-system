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
        var nextIcon = theme === 'dark' ? themeToggle.data('icon-light') : themeToggle.data('icon-dark');
        if (!nextLabel) {
            nextLabel = theme === 'dark' ? 'Light' : 'Dark';
        }
        if (nextIcon) {
            themeToggle.find('i').attr('class', 'fa ' + nextIcon);
        }
        themeToggle.attr('aria-label', nextLabel);
        themeToggle.attr('title', nextLabel);
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
            themeToggle.addClass('is-animating');
            setTimeout(function() {
                themeToggle.removeClass('is-animating');
            }, 220);
        });
    }

    


    var navToggle = $('#nav-toggle');
    var navLinks = $('#primary-nav');

    function setNavOpen(isOpen) {
        if (!navToggle.length || !navLinks.length) {
            return;
        }
        navLinks.toggleClass('is-open', isOpen);
        navToggle.attr('aria-expanded', isOpen ? 'true' : 'false');
    }

    if (navToggle.length && navLinks.length) {
        navToggle.on('click', function() {
            setNavOpen(!navLinks.hasClass('is-open'));
        });

        navLinks.find('a').on('click', function() {
            setNavOpen(false);
        });

        $(document).on('keydown', function(e) {
            if (e.key === 'Escape') {
                setNavOpen(false);
            }
        });

        $(document).on('click', function(e) {
            if (!navLinks.hasClass('is-open')) {
                return;
            }
            var $target = $(e.target);
            if ($target.closest('#primary-nav').length) {
                return;
            }
            if ($target.closest('#nav-toggle').length) {
                return;
            }
            setNavOpen(false);
        });

        $(window).on('resize', function() {
            if (window.innerWidth > 960) {
                setNavOpen(false);
            }
        });
    }

    function initCarousel($carousel) {
        var $slides = $carousel.find('.carousel-slide');
        if ($slides.length <= 1) {
            $carousel.addClass('single');
            return;
        }
        var interval = parseInt($carousel.data('interval'), 10);
        if (isNaN(interval) || interval < 1500) {
            interval = 5000;
        }
        var current = 0;
        var $dots = $carousel.find('.carousel-dot');
        var $thumbs = $carousel.find('.carousel-thumb');

        function show(index) {
            current = index;
            $slides.removeClass('is-active').attr('aria-hidden', 'true');
            $slides.eq(current).addClass('is-active').attr('aria-hidden', 'false');
            if ($dots.length) {
                $dots.removeClass('is-active');
                $dots.eq(current).addClass('is-active');
            }
            if ($thumbs.length) {
                $thumbs.removeClass('is-active');
                $thumbs.eq(current).addClass('is-active');
            }
        }

        function next() {
            var nextIndex = (current + 1) % $slides.length;
            show(nextIndex);
        }

        function prev() {
            var prevIndex = (current - 1 + $slides.length) % $slides.length;
            show(prevIndex);
        }

        var timer = setInterval(next, interval);

        function resetTimer() {
            clearInterval(timer);
            timer = setInterval(next, interval);
        }

        $carousel.find('[data-carousel="next"]').on('click', function(e) {
            e.preventDefault();
            next();
            resetTimer();
        });

        $carousel.find('[data-carousel="prev"]').on('click', function(e) {
            e.preventDefault();
            prev();
            resetTimer();
        });

        $dots.on('click', function() {
            var idx = parseInt($(this).data('index'), 10);
            if (isNaN(idx)) {
                return;
            }
            show(idx);
            resetTimer();
        });

        $thumbs.on('click', function() {
            var idx = parseInt($(this).data('index'), 10);
            if (isNaN(idx)) {
                return;
            }
            show(idx);
            resetTimer();
        });
    }

    $('.course-carousel').each(function() {
        initCarousel($(this));
    });

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


