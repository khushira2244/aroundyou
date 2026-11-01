import '@testing-library/jest-dom/vitest';
import {afterEach,vi} from 'vitest';
import {cleanup,configure} from '@testing-library/react';
afterEach(()=>{cleanup();localStorage.clear();sessionStorage.clear();vi.restoreAllMocks()});
Object.defineProperty(window,'scrollTo',{value:vi.fn(),writable:true});

configure({asyncUtilTimeout:5000});
