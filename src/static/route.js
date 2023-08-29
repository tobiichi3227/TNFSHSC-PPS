var route = new function() {
    this.curr_url = null;
    this.prev_url = null;
    this.main_navbar = null;
    this.member_id = null;
    this.session_id = null;

    this.get_session_id = function() {
        return this.session_id;
    }

    this.set_session_id = function(session_id) {
        this.session_id = session_id;
    }

    this.init = function() {
        this.main_navbar = $('.main-navbar');

        // $(document).on('keypress', 'input', function(event) {
        //     let index, next;

        //     if (event.which == 13) {
        //         if (!isNaN(index = parseInt($(this).attr('tabindex')))) {
        //             next = $(`[tabindex="${index + 1}"]`);

        //             if (next.attr('submit') != undefined) {
        //                 next.click();
        //             } else {
        //                 next.focus();
        //             }
        //         }
        //     }
        // })

        this.main_navbar.find('.nav-link.logout').on('click', event => {
            $.post('/pps/be/login', {
                'reqtype': 'logout',
            }, res => {
                location.href = '/pps/info';
            })
        })

        let member_id;
        member_id = $('#indexjs').attr('member_id');
        if (member_id != '') {
            this.member_id = parseInt(member_id);
            this.main_navbar.find('.nav-link.logout').show();
        } else {
            this.main_navbar.find('.nav-link.login').show();
        }

        this.update(0);
    }

    this.go = (url) => {
        window.history.pushState(null, document.title, url);
        this.update(1);
    }

    this.reload = () => {
        this.update(1);
    }

    this.update = function(mode) {
        function PoPState() {
            this.prev_url = location.href;
            let parts = location.href.split('/');
            let page = parts[4];
            if (page == 'index') {
                page = 'info';
            }

            let req_path = parts[4];
            for (let i = 5; i < parts.length-1; i++) {
                req_path += `/${parts[i]}`;
            }

            let args = '';
            parts = parts[parts.length - 1].match(/\?([^#]+)/);
            if (parts == null) {
                args = `cache=${new Date().getTime()}`;
            } else {
                args = parts[1] + `&cache=${new Date().getTime()}`
            }
            $.get('/pps/be/' + req_path, args, res => {
                    routerView.html(res).ready(() => {
                        route.main_navbar.find('li').find('a.active').removeClass('active');
                        route.main_navbar.find(`li.${page}`).find('a').addClass('active');

                        if (typeof(init) == 'function') {
                            init();
                        }

                        routerView.find('a').each((_, element) => {
                            $(element).on('click', (event) => {
                                event.preventDefault();
                                history.pushState(null, '', $(element).attr('href'))
                                PoPState()
                            }) 
                        })
                });
            })
        }
       
        var routerView = $('#routerView');

        if (mode == 1) {
            PoPState();
            return;
        }        

        window.addEventListener('DOMContentLoaded', onLoad);
        document.getElementById('routerView').addEventListener('DOMContentLoaded', onLoad);
        window.addEventListener('popstate', PoPState);
        function onLoad() {
            PoPState();
            let links = document.querySelectorAll('li a[href]');
            links.forEach(link => {
                link.addEventListener('click', event => {
                    event.preventDefault();
                    
                    history.pushState(null, '', link.getAttribute('href'))
                    PoPState()
                })
            })
        }

        onLoad()

    }
}