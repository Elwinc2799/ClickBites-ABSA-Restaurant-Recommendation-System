import { GetServerSideProps, GetStaticProps } from 'next';
import React, { useState } from 'react';
import axios from 'axios';
import { getCookie } from 'cookies-next';
import NavBar from '@/components/NavigationBar/NavBar';
import { Background } from '@/components/Background/Background';
import Footer from '@/components/Layout/Footer';
import Image from 'next/image';
import Link from 'next/link';
import ReviewCard from '@/components/Review/ReviewCard';
import HoursTable from '@/components/BusinessDetails/HoursTable';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faPlus } from '@fortawesome/free-solid-svg-icons';
import AddReviewForm from '@/components/BusinessDetails/AddReviewForm';

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
    is_open: number;
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

function Business(props: { business: Business }) {
    const { business } = props;
    const [showForm, setShowForm] = useState(false);

    // cast business vector scores to a list with text and scores and convert scores to string
    const vectorScores = [
        {
            text: 'Food',
            score: (business.vector[0] * 100).toFixed(2).toString(),
        },
        {
            text: 'Serv.',
            score: (business.vector[1] * 100).toFixed(2).toString(),
        },
        {
            text: 'Price',
            score: (business.vector[2] * 100).toFixed(2).toString(),
        },
        {
            text: 'Ambi.',
            score: (business.vector[3] * 100).toFixed(2).toString(),
        },
        {
            text: 'Misc.',
            score: (business.vector[4] * 100).toFixed(2).toString(),
        },
    ];

    const handleClick = () => {
        setShowForm(true);
    };

    return (
        <>
            <NavBar isLanding={false} />
            <Background color="bg-gray-100">
                <div className="px-44 py-24 flex flex-col w-full justify-start items-center">
                    <Image
                        src={`data:image/jpeg;base64,${business.business_pic}`}
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

                                    <div className="flex flex-row mt-2 mb-6">
                                        {business.categories
                                            .split(', ')
                                            .slice(0, 3)
                                            .map((category, index) => (
                                                <span
                                                    key={index}
                                                    className="badge badge-primary mr-3">
                                                    {category}
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
                                                    {business.view_count}
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
                                        {business.description}
                                    </p>
                                    <hr className="my-4 border-1 border-gray-300 w-full" />
                                    <div className="flex flex-col w-full items-start justify-start">
                                        <div className="flex flex-row w-full items-center justify-between">
                                            <h1 className="text-2xl font-bold leading-relaxed  text-gray-900">
                                                Reviews
                                            </h1>
                                            <button
                                                className="btn bg-blue-500 hover:bg-blue-700 text-white mx-4 btn-circle"
                                                onClick={handleClick}>
                                                <FontAwesomeIcon
                                                    icon={faPlus}
                                                />
                                            </button>

                                            {showForm && (
                                                <AddReviewForm
                                                    businessId={
                                                        props.business._id
                                                    }
                                                    setShowForm={setShowForm}
                                                />
                                            )}
                                        </div>

                                        <div className="w-full">
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
                            <div className="w-3/4 flex flex-row justify-between p-4">
                                {vectorScores.map((value, index) => (
                                    <div
                                        key={index}
                                        className={`border-4 border-gray-200 mx-2 text-xl radial-progress  ${
                                            // if score is less than 0, make text red, else make text green
                                            parseFloat(value.score) < 0
                                                ? 'text-red-500'
                                                : 'text-green-500'
                                        }`}
                                        style={
                                            {
                                                '--value':
                                                    parseFloat(value.score) < 0
                                                        ? (-parseFloat(
                                                              value.score
                                                          )).toString()
                                                        : value.score,
                                                '--size': '10rem',
                                                '--thickness': '1rem',
                                            } as React.CSSProperties
                                        }>
                                        {value.text}
                                    </div>
                                ))}
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
        const business = res.data;

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
