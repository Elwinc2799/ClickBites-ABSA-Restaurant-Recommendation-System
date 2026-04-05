import { GetServerSideProps, GetStaticProps } from 'next';
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { getCookie } from 'cookies-next';
import NavBar from '@/components/NavigationBar/NavBar';
import { Background } from '@/components/Background/Background';
import Footer from '@/components/Layout/Footer';
import Image from 'next/image';
import Link from 'next/link';
import ReviewCard from '@/components/Review/ReviewCard';
import HoursTable from '@/components/BusinessDetails/HoursTable';
import { UseLoginStatus } from '@/components/utils/UseLoginStatus';
import dynamic from 'next/dynamic';

// Component that will be dynamically imported
const ReviewFormButton = dynamic(
    () => import('@/components/BusinessDetails/AddReviewButton'),
    {
        loading: () => null, // Display nothing while loading
        ssr: false, // This component will not be rendered on the server
    }
);

const AspectRadar = dynamic(
    () => import('@/components/SharedComponents/AspectRadar'),
    {
        loading: () => null, // Display nothing while loading
        ssr: false, // This component will not be rendered on the server
    }
);

interface Business {
    _id: string;
    name: string;
    address: string;
    city: string;
    state: string;
    latitude: number;
    longitude: number;
    stars: number;
    review_count: number;
    categories: string;
    hours: {
        Monday: string;
        Tuesday: string;
        Wednesday: string;
        Thursday: string;
        Friday: string;
        Saturday: string;
        Sunday: string;
    };
    description: string;
    view_count: number;
    vector: number[];
    business_pic: string;
    reviews: {
        _id: string;
        user_id: string;
        business_id: string;
        user_name: string;
        stars: number;
        text: string;
        date: string;
    }[];
}

const blankBusinessPics = [
    'blank-businesspic.jpg',
];

function Business(props: { business: Business }) {
    const { business } = props;
    const [showForm, setShowForm] = useState(false);

    if (business.vector == null) {
        business.vector = [0, 0, 0, 0, 0];
    }

    // cast business vector scores to a list with text and scores and convert scores to string
    const vectorScores = [
        {
            text: 'Food',
            score: (business.vector[0] * 100).toFixed(2).toString(),
        },
        {
            text: 'Service',
            score: (business.vector[1] * 100).toFixed(2).toString(),
        },
        {
            text: 'Price',
            score: (business.vector[2] * 100).toFixed(2).toString(),
        },
        {
            text: 'Ambience',
            score: (business.vector[3] * 100).toFixed(2).toString(),
        },
        {
            text: 'Miscellaneous',
            score: (business.vector[4] * 100).toFixed(2).toString(),
        },
    ];

    const handleClick = () => {
        setShowForm(true);
    };

    const [defaultPic, setDefaultPic] = useState('');

    useEffect(() => {
        const randomPic =
            blankBusinessPics[
                Math.floor(Math.random() * blankBusinessPics.length)
            ];
        setDefaultPic(randomPic);
    }, []);

    return (
        <>
            <NavBar isLanding={false} />
            <Background color="bg-gray-100">
                <div className="px-44 py-24 flex flex-col w-full justify-start items-center">
                    <Image
                        src={
                            business.business_pic
                                ? `/business_photo/${business.business_pic}`
                                : `/images/${defaultPic}`
                        }
                        alt="restaurant image"
                        width={0}
                        height={0}
                        sizes="(max-width: 640px) 640px, 100vw"
                        className="w-full h-96 object-cover rounded-tl-lg rounded-tr-lg"
                    />
                    <div className="flex items-center justify-center w-full">
                        <div className="bg-white rounded-bl-lg rounded-br-lg p-6 shadow-lg w-full">
                            <div className="flex flex-row justify-between items-start">
                                <div>
                                    <h1 className="text-3xl font-bold">
                                        {business.name}
                                    </h1>
                                    <Link
                                        href={`https://www.google.com/maps/place/${business.latitude},${business.longitude}`}>
                                        <h3 className="text-xl mb-5 text-blue-500 underline">
                                            {business.address}, {business.city},{' '}
                                            {business.state}
                                        </h3>
                                    </Link>

                                    <div className="flex flex-wrap mt-2 mb-6">
                                        {business.categories
                                            .split(', ')
                                            .map((category, index) => (
                                                <span
                                                    key={index}
                                                    className="badge bg-[#39c1f6] text-[#f7fafc] badge-lg mr-3">
                                                    {category.length > 10
                                                        ? `${category.substring(
                                                              0,
                                                              10
                                                          )}...`
                                                        : category}
                                                </span>
                                            ))}
                                    </div>
                                </div>
                                <div>
                                    <div className="w-full flex flex-row justify-evenly items-start">
                                        <div className="stats shadow mx-2">
                                            <div className="stat">
                                                <div className="stat-title text-center">
                                                    Views
                                                </div>
                                                <div className="stat-value text-center">
                                                    {business.view_count <
                                                    business.review_count
                                                        ? business.review_count
                                                        : business.view_count}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="stats shadow mx-2">
                                            <div className="stat">
                                                <div className="stat-title text-center">
                                                    Reviews
                                                </div>
                                                <div className="stat-value text-center">
                                                    {business.review_count}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="stats shadow mx-2">
                                            <div className="stat">
                                                <div className="stat-title text-center">
                                                    Rating
                                                </div>
                                                <div className="stat-value text-center">
                                                    {Number(
                                                        business.stars.toFixed(
                                                            2
                                                        )
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div className="flex flex-row justify-between items-start w-full">
                                <div className="flex flex-col justify-start items-start mr-10 w-full">
                                    <p className="text-gray-600 text-justify mb-5">
                                        {business.description == 'hello world'
                                            ? 'Welcome to ' +
                                              business.name +
                                              '! Enjoy delicious food and drinks at our restaurant.'
                                            : business.description}
                                    </p>
                                    <hr className="my-4 border-1 border-gray-300 w-full" />
                                    <div className="flex flex-col w-full items-start justify-start">
                                        <div className="flex flex-row w-full items-center justify-between">
                                            <h1 className="text-2xl font-bold leading-relaxed  text-gray-900">
                                                Reviews
                                            </h1>

                                            <ReviewFormButton
                                                businessId={props.business._id}
                                            />
                                        </div>

                                        <div className="w-full">
                                            {business.reviews.length === 0 && (
                                                <div className="flex flex-col items-start justify-center">
                                                    <p className="mb-4 text-lg font-medium leading-relaxed text-gray-900">
                                                        No reviews yet
                                                    </p>
                                                </div>
                                            )}
                                            {business.reviews.map(
                                                (review, index) => (
                                                    <ReviewCard
                                                        key={index.toString()}
                                                        review={review}
                                                        isUser={false}
                                                    />
                                                )
                                            )}
                                        </div>
                                    </div>
                                </div>

                                {business.hours && (
                                    <HoursTable business={business} />
                                )}
                            </div>
                            <hr className="mt-9 mb-4 border-1 border-gray-300 w-full" />
                            <h1 className="text-2xl font-bold leading-relaxed  text-gray-900">
                                Aspect Analysis
                            </h1>
                            <div className="w-full h-full flex justify-center items-center">
                                <AspectRadar
                                    vectorScores={vectorScores}
                                    isBusiness={true}
                                    isUser={true}
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </Background>
            <Footer />
        </>
    );
}

// retrieve the business data for the given id
export const getServerSideProps: GetServerSideProps = async (context) => {
    try {
        const res = await axios.get(
            `${process.env.API_URL}/api/business/${context.params?.id}`,
            {
                headers: {
                    Authorization: `Bearer ${getCookie('token')}`,
                },
                withCredentials: true,
            }
        );
        const raw = res.data;
        const scores = raw.aspect_scores || {};

        const business = {
            ...raw,
            _id: raw.business_id || raw._id,
            categories: Array.isArray(raw.categories)
                ? raw.categories.join(', ')
                : (raw.categories || ''),
            vector: [
                scores.food ?? 0,
                scores.service ?? 0,
                scores.price ?? 0,
                scores.ambience ?? 0,
                scores.misc ?? 0,
            ],
            business_pic: raw.photo_url || raw.business_pic || null,
            view_count: raw.view_count || raw.review_count || 0,
            description: raw.description || 'hello world',
            hours: raw.hours || null,
            reviews: (raw.reviews || []).map((r: any) => ({
                ...r,
                _id: r.review_id || r._id,
                user_name: r.user_name || 'Anonymous',
                date: r.created_at || r.date || '',
            })),
        };

        return {
            props: {
                business,
            },
        };
    } catch (error) {
        console.error(error);
        return {
            notFound: true,
        };
    }
};
export default Business;
