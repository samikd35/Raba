import React, { useState, useRef, useEffect } from 'react';
import { faqData } from './faqData.js';

const FAQsPage = () => {
  const [openItems, setOpenItems] = useState(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [isVisible, setIsVisible] = useState(false);
  const pageRef = useRef(null);
  const searchInputRef = useRef(null);

  // Detect reduced motion preference
  const prefersReducedMotion = typeof window !== 'undefined' && 
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Categorize FAQs
  const categorizeQuestion = (question: string, answer: string) => {
    const text = `${question} ${answer}`.toLowerCase();
    
    if (text.includes('plan') || text.includes('cost') || text.includes('payment') || text.includes('refund') || text.includes('free')) {
      return 'Pricing & Billing';
    }
    if (text.includes('what is') || text.includes('how does') || text.includes('getting started') || text.includes('technical background')) {
      return 'Getting Started';
    }
    if (text.includes('feature') || text.includes('support') || text.includes('save') || text.includes('data') || text.includes('ai')) {
      return 'Platform & Features';
    }
    if (text.includes('african') || text.includes('market') || text.includes('global') || text.includes('country')) {
      return 'Availability & Markets';
    }
    return 'General';
  };

  // Add categories to FAQ data
  const categorizedFAQs = faqData.map(faq => ({
    ...faq,
    category: categorizeQuestion(faq.question, faq.answer),
    id: faq.question.toLowerCase().replace(/[^a-z0-9]+/g, '-')
  }));

  // Get unique categories
  const categories = ['All', ...new Set(categorizedFAQs.map(faq => faq.category))];

  // Filter FAQs based on search and category
  const filteredFAQs = categorizedFAQs.filter(faq => {
    const matchesSearch = searchQuery === '' || 
      faq.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
      faq.answer.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesCategory = selectedCategory === 'All' || faq.category === selectedCategory;
    
    return matchesSearch && matchesCategory;
  });

  // Debounced search
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      // Search is already handled in filteredFAQs
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchQuery]);

  // Handle hash navigation and deep linking
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash.substring(1);
      if (hash) {
        const faqIndex = categorizedFAQs.findIndex(faq => faq.id === hash);
        if (faqIndex !== -1) {
          setOpenItems(prev => new Set([...prev, faqIndex]));
          
          // Scroll to the FAQ with offset
          setTimeout(() => {
            const element = document.getElementById(`faq-${hash}`);
            if (element) {
              const offset = 100; // Account for sticky headers
              const elementPosition = element.getBoundingClientRect().top + window.pageYOffset;
              window.scrollTo({
                top: elementPosition - offset,
                behavior: 'smooth'
              });
            }
          }, 100);
        }
      }
    };

    // Handle initial hash on page load
    handleHashChange();

    // Listen for hash changes
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  // Update URL hash when accordion opens
  const toggleAccordion = (index: number) => {
    const faq = filteredFAQs[index];
    const newOpenItems = new Set(openItems);
    
    if (openItems.has(index)) {
      newOpenItems.delete(index);
      // Remove hash if closing
      if (window.location.hash === `#${faq.id}`) {
        window.history.pushState('', document.title, window.location.pathname);
      }
    } else {
      newOpenItems.add(index);
      // Add hash when opening
      window.history.pushState('', document.title, `#${faq.id}`);
    }
    
    setOpenItems(newOpenItems);
  };

  // Intersection Observer for animations
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsVisible(entry.isIntersecting);
      },
      { threshold: 0.1 }
    );

    if (pageRef.current) {
      observer.observe(pageRef.current);
    }

    return () => observer.disconnect();
  }, []);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      toggleAccordion(index);
    }
  };

  return (
    <div 
      ref={pageRef}
      className="min-h-screen bg-gradient-to-b from-slate-50 to-white py-16 md:py-24"
    >
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Page Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-slate-900 mb-6">
            Frequently Asked Questions
          </h1>
        </div>

        {/* Search and Filters */}
        <div className="mb-12">
          
          {/* Search Input */}
          <div className="relative mb-6">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
              <svg className="h-5 w-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
              </svg>
            </div>
            <input
              ref={searchInputRef}
              type="text"
              placeholder="Search FAQs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="
                w-full pl-12 pr-4 py-4 
                border border-slate-200 rounded-2xl
                bg-white shadow-sm
                focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500
                text-slate-900 placeholder-slate-400
                transition-all duration-200
              "
            />
          </div>

          {/* Category Filter Chips */}
          <div className="flex flex-wrap gap-2 justify-center">
            {categories.map((category) => (
              <button
                key={category}
                onClick={() => setSelectedCategory(category)}
                className={`
                  px-4 py-2 rounded-full text-sm font-medium
                  transition-all duration-200
                  focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2
                  ${selectedCategory === category
                    ? 'bg-indigo-500 text-white shadow-md'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                  }
                `}
              >
                {category}
              </button>
            ))}
          </div>
        </div>

        {/* FAQ List */}
        <div className="max-w-3xl mx-auto">
          {filteredFAQs.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-slate-500 text-lg">
                No FAQs found matching your search criteria.
              </p>
            </div>
          ) : (
            <div className="bg-white rounded-2xl shadow-lg shadow-slate-200/50 border border-slate-100 overflow-hidden">
              {filteredFAQs.map((faq, index) => (
                <div 
                  key={faq.id} 
                  id={`faq-${faq.id}`}
                  className={`
                    border-b border-slate-100 last:border-b-0
                    transition-all duration-300 ease-out
                    ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}
                  `}
                  style={{
                    transitionDelay: prefersReducedMotion ? '0ms' : `${Math.min(index * 50, 500)}ms`
                  }}
                >
                  
                  {/* Question Button */}
                  <button
                    onClick={() => toggleAccordion(index)}
                    onKeyDown={(e) => handleKeyDown(e, index)}
                    className="
                      w-full px-6 md:px-8 py-6 text-left
                      hover:bg-slate-50 focus:bg-slate-50
                      focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-inset
                      transition-colors duration-200
                    "
                    aria-expanded={openItems.has(index)}
                    aria-controls={`faq-full-answer-${index}`}
                    id={`faq-full-question-${index}`}
                  >
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg md:text-xl font-semibold text-slate-900 pr-4">
                        {faq.question}
                      </h3>
                      
                      {/* Toggle Icon */}
                      <div className={`
                        flex-shrink-0 w-6 h-6 flex items-center justify-center
                        text-indigo-500 transition-transform duration-200
                        ${openItems.has(index) ? 'rotate-45' : 'rotate-0'}
                      `}>
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M12 5v14m-7-7h14"/>
                        </svg>
                      </div>
                    </div>
                  </button>

                  {/* Answer Panel */}
                  <div
                    id={`faq-full-answer-${index}`}
                    role="region"
                    aria-labelledby={`faq-full-question-${index}`}
                    className={`
                      overflow-hidden transition-all duration-300 ease-out
                      ${openItems.has(index) 
                        ? 'max-h-96 opacity-100' 
                        : 'max-h-0 opacity-0'
                      }
                    `}
                  >
                    <div className="px-6 md:px-8 pb-6">
                      <p className="text-slate-600 leading-relaxed">
                        {faq.answer}
                      </p>
                    </div>
                  </div>

                </div>
              ))}
            </div>
          )}
        </div>

        {/* Back to Top */}
        <div className="text-center mt-16">
          <button
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            className="
              inline-flex items-center gap-2 text-indigo-600 hover:text-indigo-700
              font-medium transition-colors duration-200
              focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2
              rounded-md px-2 py-1
            "
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 15l-6-6-6 6"/>
            </svg>
            Back to top
          </button>
        </div>

      </div>
    </div>
  );
};

export default FAQsPage;
