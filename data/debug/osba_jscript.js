const btn = document.getElementById('menu-btn')

btn.addEventListener('click', navToggle)

function navToggle() {
    btn.classList.toggle('open')
}

function data() {
    return {
        sortBy: "",
        sortAsc: false,
        sortByColumn($event) {
            if (this.sortBy === $event.target.innerText) {
                if (this.sortAsc) {
                    this.sortBy = "";
                    this.sortAsc = false;
                } else {
                    this.sortAsc = !this.sortAsc;
                }
            } else {
                this.sortBy = $event.target.innerText;
            }

            let rows = this.getTableRows()
                .sort(
                    this.sortCallback(
                        Array.from($event.target.parentNode.children).indexOf(
                            $event.target
                        )
                    )
                )
                .forEach((tr) => {
                    this.$refs.tbody.appendChild(tr);
                });
        },
        getTableRows() {
            return Array.from(this.$refs.tbody.querySelectorAll("tr"));
        },
        getCellValue(row, index) {
            return row.children[index].innerText;
        },
        sortCallback(index) {
            return (a, b) =>
                ((row1, row2) => {
                    return row1 !== "" &&
                        row2 !== "" &&
                        !isNaN(row1) &&
                        !isNaN(row2)
                        ? row1 - row2
                        : row1.toString().localeCompare(row2);
                })(
                    this.getCellValue(this.sortAsc ? a : b, index),
                    this.getCellValue(this.sortAsc ? b : a, index)
                );
        }
    };
}

// User Menu Shrink

function navShrink() {
    return {
        scale: 1,
        padding: 1,
        fontScale: 1,
        get navStyle() {
            return window.innerWidth >= 768
                ? `padding-top:${this.padding}rem;padding-bottom:${this.padding}rem;`
                : '';
        },
        get logoStyle() {
            return window.innerWidth >= 768
                ? `transform:scale(${this.scale});transform-origin:center;`
                : '';
        },
        get linkStyle() {
            return window.innerWidth >= 768
                ? `transform:scale(${this.fontScale});transform-origin:center;`
                : '';
        },
        init() {
            const maxScroll = 150;
            const minScale = 0.70;
            const minPadding = 0; // rem
            const maxPadding = 1;    // rem
            const minFontScale = 0.95;

            const update = () => {
                if (window.innerWidth < 768) return;

                const scrollY = Math.min(window.scrollY, maxScroll);
                const progress = scrollY / maxScroll;

                // interpolate sizes
                this.scale = 1 - (1 - minScale) * progress;
                this.padding = maxPadding - (maxPadding - minPadding) * progress;
                this.fontScale = 1 - (1 - minFontScale) * progress;
            };

            // run once
            update();

            window.addEventListener('scroll', () => {
                requestAnimationFrame(update);
            }, { passive: true });

            window.addEventListener('resize', update);
        }
    }
}


// User Menu Listener & Overflow

function navMenu() {
    return {
        mobileOpen: false,
        openMenu: null,
        overflowItems: [],
        init() {
            this.handleOverflow();
            this.setupResizeObserver();
            window.addEventListener('resize', () => {
                this.handleOverflow();
                this.openMenu = null;
                if (window.innerWidth < 768) this.mobileOpen = false;
            });
        },

        setupResizeObserver() {
            const menu = document.getElementById('user-menu');
            if (!menu) return;
            let scheduled = false;
            this.resizeObserver = new ResizeObserver(() => {
                if (scheduled) return;
                scheduled = true;
                requestAnimationFrame(() => {
                    this.handleOverflow();
                    scheduled = false;
                });
            });
            this.resizeObserver.observe(menu);
        },

        handleOverflow() {
            const menu = document.getElementById('user-menu');
            if (!menu) return;
            const moreMenu = document.getElementById('moreMenuButton');
            if (!moreMenu) return;

            const items = Array.from(menu.children).filter(li => li.id !== 'moreMenuLi');
            const availableWidth = menu.clientWidth;
            let usedWidth = 0;
            const moreWidth = moreMenu.getBoundingClientRect().width || 80;

            this.overflowItems = [];
            items.forEach(i => i.style.display = 'inline-flex');

            let lastVisibleIndex = items.length;

            for (let i = 0; i < items.length; i++) {
                const itemWidth = items[i].getBoundingClientRect().width;
                usedWidth += itemWidth;
                if (usedWidth + moreWidth > availableWidth) {
                    lastVisibleIndex = i;
                    break;
                }
            }

            if (lastVisibleIndex < items.length) {
                for (let i = lastVisibleIndex; i < items.length; i++) {
                    this.overflowItems.push(items[i].outerHTML);
                    items[i].style.display = 'none';
                }
                document.getElementById('moreMenuLi').style.display = 'inline-flex';
            } else {
                document.getElementById('moreMenuLi').style.display = 'none';
            }
        },

        watch: {
            mobileOpen(value) {
                document.body.style.overflow = value ? 'hidden' : '';
            }
        },

        toggleMobileMenu() {
            this.mobileOpen = !this.mobileOpen;
            this.openMenu = null;
        },

        toggleSubmenu(name) {
            if (this.openMenu === name) {
                this.openMenu = null;
            } else {
                this.openMenu = name;
            }
        },

        closeMenus() {
            this.openMenu = null;
        }
    }
}

// Image Carousel-Lightbox Script

function imageCarousel() {
    return {
        current: 0,
        lightboxOpen: false,
        activeImage: '',
        activeTitle: '',
        slides: [],

        init() {
            this.slides = Array.from(this.$refs.source.children).map(el => ({
                thumb: el.dataset.thumb,
                title: el.dataset.title
            }));
        },

        next() {
            if (this.current < this.slides.length - 1) this.current++;
        },
        prev() {
            if (this.current > 0) this.current--;
        },
        goTo(i) {
            this.current = i;
        },

        openLightbox(slide) {
            this.activeImage = slide.thumb;
            this.activeTitle = slide.title;
            this.lightboxOpen = true;
        },
        closeLightbox() {
            this.lightboxOpen = false;
            this.activeImage = '';
            this.activeTitle = '';
        },

        swipeStartX: null,
        swipeDeltaX: null,
        startSwipe(e) { this.swipeStartX = e.clientX; },
        trackSwipe(e) {
            if (this.swipeStartX !== null) this.swipeDeltaX = e.clientX - this.swipeStartX;
        },
        endSwipe() {
            if (this.swipeDeltaX > 50) this.prev();
            else if (this.swipeDeltaX < -50) this.next();
            this.cancelSwipe();
        },
        cancelSwipe() {
            this.swipeStartX = null;
            this.swipeDeltaX = null;
        }
    };
}


// Video Carousel-Lightbox Script

function vidCarousel() {
    return {
        current: 0,
        lightboxOpen: false,
        activeVideo: null,
        embedUrl: '',
        slides: [],

        async init() {
            this.slides = Array.from(document.querySelectorAll('[data-type]'));

            // Fetch thumbnails
            for (let el of this.slides) {
                if (el.dataset.type === 'youtube') {
                    el.dataset.thumb = `https://img.youtube.com/vi/${el.dataset.id}/hqdefault.jpg`;
                } else if (el.dataset.type === 'vimeo') {
                    try {
                        const res = await fetch(`https://vimeo.com/api/oembed.json?url=https://vimeo.com/${el.dataset.id}`);
                        const data = await res.json();
                        el.dataset.thumb = data.thumbnail_url;
                    } catch {
                        el.dataset.thumb = `https://vumbnail.com/${el.dataset.id}.jpg`;
                    }
                }
            };
        },

        next() {
            if (this.current < this.slides.length - 1) this.current++;
        },
        prev() {
            if (this.current > 0) this.current--;
        },
        goTo(i) {
            this.current = i;
        },

        openLightbox(dataset) {
            this.activeVideo = dataset;
            if (dataset.type === 'youtube') {
                this.embedUrl = `https://www.youtube.com/embed/${dataset.id}?autoplay=1&playsinline=1&enablejsapi=1`;
            } else if (dataset.type === 'vimeo') {
                this.embedUrl = `https://player.vimeo.com/video/${dataset.id}?autoplay=1`;
            }
            this.lightboxOpen = true;
        },

        closeLightbox() {
            this.lightboxOpen = false;
            this.activeVideo = null;
            this.embedUrl = '';
        },

        swipeStartX: null,
        swipeDeltaX: null,
        startSwipe(e) { this.swipeStartX = e.clientX; },
        trackSwipe(e) {
            if (this.swipeStartX !== null) this.swipeDeltaX = e.clientX - this.swipeStartX;
        },
        endSwipe() {
            if (this.swipeDeltaX > 50) this.prev();
            else if (this.swipeDeltaX < -50) this.next();
            this.cancelSwipe();
        },
        cancelSwipe() {
            this.swipeStartX = null;
            this.swipeDeltaX = null;
        }
    };
}


// Game Ticker

function carousel() {
    return {
        currentIndex: 0,
        totalCards: 0,
        cardWidth: 0,
        gap: 0,
        step: 0,
        visibleCards: 1,

        init() {
            this.syncFromDOM();
            window.addEventListener('resize', () => this.syncFromDOM());
            requestAnimationFrame(() => this.syncFromDOM());
            setTimeout(() => this.syncFromDOM(), 150);
        },

        syncFromDOM() {
            const track = this.$refs.track;
            const viewport = this.$refs.viewport;
            if (!track || !viewport || track.children.length === 0) return;

            this.totalCards = track.children.length;

            const firstCard = track.children[0];
            const rect = firstCard.getBoundingClientRect();
            const styles = getComputedStyle(firstCard);
            this.cardWidth = rect.width;
            this.gap = parseFloat(styles.marginRight || '0') || 0;
            this.step = this.cardWidth + this.gap;

            const viewportWidth = viewport.clientWidth;
            this.visibleCards = Math.min(
                Math.max(1, Math.floor((viewportWidth + this.gap) / this.step)),
                this.totalCards
            );

            const lastIndex = Math.max(0, this.totalCards - this.visibleCards);
            if (this.currentIndex > lastIndex) this.currentIndex = lastIndex;
        },

        next() {
            const lastIndex = Math.max(0, this.totalCards - this.visibleCards);
            if (this.currentIndex < lastIndex) {
                this.currentIndex++;
            } else {
                this.currentIndex = 0;
            }
        },

        prev() {
            const lastIndex = Math.max(0, this.totalCards - this.visibleCards);
            if (this.currentIndex > 0) {
                this.currentIndex--;
            } else {
                this.currentIndex = lastIndex;
            }
        }
    };
}

// Head to Head Bars

function barStat(teamA, teamB, label, valueA, valueB) {
    return {
        teamA,
        teamB,
        label,
        valueA,
        valueB,
        widthA: 0,
        widthB: 0,
        animate() {
            setTimeout(() => {
                this.widthA = this.valueA;
                this.widthB = this.valueB;
            }, 200);
        }
    }
}
